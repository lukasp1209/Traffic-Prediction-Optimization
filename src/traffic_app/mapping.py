from __future__ import annotations

import re
from difflib import SequenceMatcher
import math
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import pydeck as pdk
import requests
import streamlit as st

from .config import OVERPASS_API_URL
from .domain import CityStreetReference
from .streamlit_compat import cache_data
from .text_utils import build_overpass_name_regex, canonicalize_text


def normalize_street_key(value: str) -> str:
    normalized = canonicalize_text(value)
    normalized = normalized.replace("strasse", "str").replace("straße", "str")
    normalized = normalized.replace("allee", "allee")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def street_similarity(left: str, right: str) -> float:
    left_norm = normalize_street_key(left)
    right_norm = normalize_street_key(right)
    if not left_norm or not right_norm:
        return 0.0
    if left_norm == right_norm:
        return 1.0
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    token_score = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
    ratio_score = SequenceMatcher(None, left_norm, right_norm).ratio()
    return max(token_score, ratio_score)


def build_street_match_lookup(traffic_streets: List[str], osm_streets: List[str]) -> Dict[str, str]:
    osm_by_norm: Dict[str, List[str]] = {}
    for street in osm_streets:
        osm_by_norm.setdefault(normalize_street_key(street), []).append(street)

    matches: Dict[str, str] = {}
    for traffic_street in traffic_streets:
        traffic_norm = normalize_street_key(traffic_street)
        exact_matches = osm_by_norm.get(traffic_norm, [])
        if exact_matches:
            matches[traffic_street] = exact_matches[0]
            continue

        best_match = ""
        best_score = 0.0
        for osm_street in osm_streets:
            score = street_similarity(traffic_street, osm_street)
            if score > best_score:
                best_score = score
                best_match = osm_street

        if best_score >= 0.72:
            matches[traffic_street] = best_match
    return matches


def merge_stats_into_geometry(
    geometry_df: pd.DataFrame,
    period_stats: pd.DataFrame,
    street_reference: pd.DataFrame,
) -> pd.DataFrame:
    if geometry_df.empty:
        return pd.DataFrame()

    if period_stats.empty and street_reference.empty:
        merged = geometry_df.copy()
        merged["samples"] = 0
        merged["avg_traffic"] = 0.0
        merged["peak_traffic"] = 0.0
        merged["street_ref_q75"] = np.nan
        return merged

    osm_streets = geometry_df["street"].astype(str).tolist()

    stats_df = period_stats.copy() if not period_stats.empty else pd.DataFrame(columns=["street", "avg_traffic", "peak_traffic", "samples"])
    ref_df = street_reference.copy() if not street_reference.empty else pd.DataFrame(columns=["street", "street_ref_q75"])

    traffic_streets = sorted(set(stats_df.get("street", pd.Series(dtype=str)).astype(str).tolist()) | set(ref_df.get("street", pd.Series(dtype=str)).astype(str).tolist()))
    match_lookup = build_street_match_lookup(traffic_streets, osm_streets)

    if not stats_df.empty:
        stats_df["matched_street"] = stats_df["street"].map(match_lookup)
        stats_df = stats_df.dropna(subset=["matched_street"])
        stats_df = (
            stats_df.groupby("matched_street", as_index=False)
            .agg(avg_traffic=("avg_traffic", "mean"), peak_traffic=("peak_traffic", "max"), samples=("samples", "sum"))
        )
    else:
        stats_df = pd.DataFrame(columns=["matched_street", "avg_traffic", "peak_traffic", "samples"])

    if not ref_df.empty:
        ref_df["matched_street"] = ref_df["street"].map(match_lookup)
        ref_df = ref_df.dropna(subset=["matched_street"])
        ref_df = ref_df.groupby("matched_street", as_index=False)["street_ref_q75"].mean()
    else:
        ref_df = pd.DataFrame(columns=["matched_street", "street_ref_q75"])

    return (
        geometry_df.merge(stats_df, left_on="street", right_on="matched_street", how="left")
        .merge(ref_df, left_on="street", right_on="matched_street", how="left", suffixes=("", "_ref"))
        .drop(columns=[col for col in ["matched_street", "matched_street_ref"] if col in geometry_df.columns], errors="ignore")
    )


@cache_data(show_spinner=False, ttl=86_400)
def fetch_street_geometry_overpass(city_name: str, street_name: str) -> Optional[List[List[float]]]:
    city_pattern = build_overpass_name_regex(city_name)
    street_pattern = build_overpass_name_regex(street_name)
    if not city_pattern or not street_pattern:
        return None

    query = f"""
[out:json][timeout:30];
area["boundary"="administrative"]["name"~"^({city_pattern})$",i]->.searchArea;
way["highway"]["name"~"^({street_pattern})$",i](area.searchArea);
out geom;
"""

    try:
        response = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            timeout=35,
            headers={"User-Agent": "traffic-prediction-optimization/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    ways = []
    for element in payload.get("elements", []):
        if element.get("type") != "way":
            continue
        geometry = element.get("geometry", [])
        if not isinstance(geometry, list) or len(geometry) < 2:
            continue
        coords = [[float(point["lon"]), float(point["lat"])] for point in geometry if "lon" in point and "lat" in point]
        if len(coords) >= 2:
            ways.append(coords)

    return max(ways, key=len) if ways else None


@cache_data(show_spinner=False, ttl=86_400)
def fetch_all_city_streets_overpass(city_name: str) -> pd.DataFrame:
    city_pattern = build_overpass_name_regex(city_name)
    if not city_pattern:
        return pd.DataFrame(columns=["street", "street_geometry"])

    query = f"""
[out:json][timeout:60];
area["boundary"="administrative"]["name"~"^({city_pattern})$",i]->.searchArea;
way["highway"]["name"](area.searchArea);
out geom;
"""

    try:
        response = requests.post(
            OVERPASS_API_URL,
            data={"data": query},
            timeout=65,
            headers={"User-Agent": "traffic-prediction-optimization/1.0"},
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return pd.DataFrame(columns=["street", "street_geometry"])

    rows: List[Dict[str, object]] = []
    for element in payload.get("elements", []):
        if element.get("type") != "way":
            continue
        tags = element.get("tags", {})
        street_name = str(tags.get("name", "")).strip()
        geometry = element.get("geometry", [])
        if not street_name or not isinstance(geometry, list) or len(geometry) < 2:
            continue

        coords = [[float(point["lon"]), float(point["lat"])] for point in geometry if "lon" in point and "lat" in point]
        if len(coords) < 2:
            continue

        rows.append({"street": street_name, "street_geometry": coords, "geom_points": len(coords)})

    if not rows:
        return pd.DataFrame(columns=["street", "street_geometry"])

    all_streets_df = pd.DataFrame(rows)
    all_streets_df["street_key"] = all_streets_df["street"].apply(canonicalize_text)
    return (
        all_streets_df.sort_values("geom_points", ascending=False)
        .drop_duplicates(subset=["street_key"], keep="first")
        .drop(columns=["street_key", "geom_points"])
        .reset_index(drop=True)
    )


def get_street_geometry(city_name: str, street_name: str, reference: CityStreetReference) -> Optional[List[List[float]]]:
    overpass_geometry = fetch_street_geometry_overpass(city_name, street_name)
    if overpass_geometry is not None:
        return overpass_geometry

    city_key = canonicalize_text(city_name)
    street_key = canonicalize_text(street_name)
    return reference.geometries.get(city_key, {}).get(street_key)


def resolve_selected_street_geometries(
        selected_city: str,
        selected_streets: List[str],
        reference: CityStreetReference,
) -> pd.DataFrame:
    geometry_df = fetch_all_city_streets_overpass(selected_city)
    if not geometry_df.empty:
        geometry_df = geometry_df.copy()
        geometry_df["street_key"] = geometry_df["street"].apply(canonicalize_text)
        requested_df = pd.DataFrame(
            {
                "street": selected_streets,
                "street_key": [canonicalize_text(street) for street in selected_streets],
            }
        )
        matched_df = requested_df.merge(
            geometry_df[["street_key", "street_geometry"]],
            on="street_key",
            how="left",
        ).drop(columns=["street_key"])
        matched_df = matched_df.dropna(subset=["street_geometry"]).reset_index(drop=True)
        if not matched_df.empty:
            return matched_df

    geometry_rows = []
    for street in selected_streets:
        geom = get_street_geometry(selected_city, street, reference)
        if geom is not None:
            geometry_rows.append({"street": street, "street_geometry": geom})
    return pd.DataFrame(geometry_rows)


def build_street_map_data(
        city_street_df: pd.DataFrame,
        selected_city: str,
        selected_streets: List[str],
        start_ts: pd.Timestamp,
        end_ts: pd.Timestamp,
        reference: CityStreetReference,
        include_all_city_streets: bool = False,
        max_streets: int = 500,
        traffic_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    source_df = traffic_df.copy() if traffic_df is not None else city_street_df.copy()
    if source_df.empty:
        return pd.DataFrame()

    selected_streets = [street for street in selected_streets if str(street).strip()]
    show_all_streets = include_all_city_streets or not selected_streets

    source_df["city"] = source_df["city"].astype(str).str.strip()
    source_df["street"] = source_df["street"].astype(str).str.strip()
    source_df["ds"] = pd.to_datetime(source_df["ds"], errors="coerce")
    source_df["y"] = pd.to_numeric(source_df["y"], errors="coerce")
    source_df = source_df.dropna(subset=["city", "street", "ds", "y"])

    city_filtered = source_df[source_df["city"] == selected_city].copy()
    if not show_all_streets:
        city_filtered = city_filtered[city_filtered["street"].isin(selected_streets)].copy()
    if city_filtered.empty and not show_all_streets:
        return pd.DataFrame()

    period_filtered = city_filtered[(city_filtered["ds"] >= start_ts) & (city_filtered["ds"] <= end_ts)].copy()
    if period_filtered.empty:
        period_stats = pd.DataFrame(columns=["street", "avg_traffic", "peak_traffic", "samples"])
    else:
        period_stats = (
            period_filtered.groupby("street", as_index=False)
            .agg(avg_traffic=("y", "mean"), peak_traffic=("y", "max"), samples=("y", "size"))
        )

    if city_filtered.empty:
        street_reference = pd.DataFrame(columns=["street", "street_ref_q75"])
    else:
        street_reference = (
            city_filtered.groupby("street", as_index=False)["y"]
            .quantile(0.75)
            .rename(columns={"y": "street_ref_q75"})
        )

    if show_all_streets:
        geometry_df = fetch_all_city_streets_overpass(selected_city)
        if geometry_df.empty:
            geometry_rows = []
            fallback_streets = sorted(set(city_filtered["street"].dropna().tolist()))
            for street in fallback_streets:
                geom = get_street_geometry(selected_city, street, reference)
                if geom is not None:
                    geometry_rows.append({"street": street, "street_geometry": geom})
            geometry_df = pd.DataFrame(geometry_rows)
    else:
        geometry_df = resolve_selected_street_geometries(selected_city, selected_streets, reference)

    if geometry_df.empty:
        return pd.DataFrame()

    if max_streets > 0 and len(geometry_df) > max_streets:
        geometry_df = geometry_df.head(max_streets).copy()

    map_df = merge_stats_into_geometry(geometry_df, period_stats, street_reference)
    map_df["samples"] = map_df["samples"].fillna(0).astype(int)
    map_df["avg_traffic"] = map_df["avg_traffic"].fillna(0.0)
    map_df["peak_traffic"] = map_df["peak_traffic"].fillna(0.0)
    map_df["street_ref_q75"] = map_df["street_ref_q75"].replace(0, np.nan)
    map_df["congestion_index"] = (map_df["avg_traffic"] / map_df["street_ref_q75"]).replace([np.inf, -np.inf], np.nan)
    map_df["congestion_index"] = map_df["congestion_index"].fillna(0).clip(0, 1.8)
    map_df["traffic_level"] = map_df.apply(
        lambda row: "unbekannt" if row["samples"] <= 0 else ("niedrig" if row["congestion_index"] < 0.7 else ("mittel" if row["congestion_index"] < 1.0 else "hoch")),
        axis=1,
    )
    map_df["color"] = map_df.apply(
        lambda row: [160, 160, 160] if row["samples"] <= 0 else ([60, 179, 113] if row["congestion_index"] < 0.7 else ([255, 193, 7] if row["congestion_index"] < 1.0 else [220, 53, 69])),
        axis=1,
    )
    map_df["width"] = (8 + map_df["congestion_index"] * 16).round(1)
    map_df.loc[map_df["samples"] <= 0, "width"] = 5
    map_df["avg_traffic"] = map_df["avg_traffic"].round(1)
    map_df["peak_traffic"] = map_df["peak_traffic"].round(1)
    map_df["start_coord"] = map_df["street_geometry"].apply(lambda geometry: geometry[0])
    map_df["end_coord"] = map_df["street_geometry"].apply(lambda geometry: geometry[-1])
    map_df["label_coord"] = map_df["street_geometry"].apply(lambda geometry: geometry[len(geometry) // 2])
    return map_df


def compute_map_view_state(map_df: pd.DataFrame, selected_city: str) -> pdk.ViewState:
    coords = np.array([coord for path in map_df["street_geometry"] for coord in path], dtype=float)
    min_lon, min_lat = coords.min(axis=0)
    max_lon, max_lat = coords.max(axis=0)
    center_lon = float((min_lon + max_lon) / 2)
    center_lat = float((min_lat + max_lat) / 2)
    span = max(max(float(max_lon - min_lon), 0.01), max(float(max_lat - min_lat), 0.01))
    zoom = min(max(11.8 - math.log(span, 2), 10.0), 13.2)

    return pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=zoom, pitch=10, bearing=0)


def snap_timestamp(available_timestamps: List[pd.Timestamp], target: pd.Timestamp, prefer: str = "nearest") -> pd.Timestamp:
    ts_index = pd.DatetimeIndex(available_timestamps)
    position = int(ts_index.searchsorted(target, side="left"))

    if position <= 0:
        return pd.Timestamp(ts_index[0])
    if position >= len(ts_index):
        return pd.Timestamp(ts_index[-1])

    before = pd.Timestamp(ts_index[position - 1])
    after = pd.Timestamp(ts_index[position])

    if prefer == "floor":
        return before
    if prefer == "ceil":
        return after
    return before if (target - before) <= (after - target) else after


def select_map_time_window(available_timestamps: List[pd.Timestamp]) -> tuple[pd.Timestamp, pd.Timestamp]:
    latest_ts = pd.Timestamp(available_timestamps[-1])
    earliest_ts = pd.Timestamp(available_timestamps[0])
    presets = {
        "Letzte 24 Stunden": pd.Timedelta(hours=24),
        "Letzte 7 Tage": pd.Timedelta(days=7),
        "Letzte 30 Tage": pd.Timedelta(days=30),
        "Gesamter Zeitraum": None,
        "Benutzerdefiniert": "custom",
    }

    preset = st.selectbox("Zeitraum", list(presets.keys()), index=0)
    if presets[preset] is None:
        return earliest_ts, latest_ts
    if preset != "Benutzerdefiniert":
        start_target = latest_ts - presets[preset]
        return snap_timestamp(available_timestamps, start_target, prefer="ceil"), latest_ts

    default_start = snap_timestamp(available_timestamps, latest_ts - pd.Timedelta(hours=24), prefer="ceil")
    custom_cols = st.columns(2)
    with custom_cols[0]:
        start_date = st.date_input("Startdatum", value=default_start.date(), key="map_start_date")
        start_time = st.time_input("Startzeit", value=default_start.time(), key="map_start_time")
    with custom_cols[1]:
        end_date = st.date_input("Enddatum", value=latest_ts.date(), key="map_end_date")
        end_time = st.time_input("Endzeit", value=latest_ts.time(), key="map_end_time")

    start_candidate = pd.Timestamp.combine(start_date, start_time)
    end_candidate = pd.Timestamp.combine(end_date, end_time)
    if end_candidate < start_candidate:
        st.warning("Ende liegt vor dem Start. Der Zeitraum wurde automatisch korrigiert.")
        start_candidate, end_candidate = end_candidate, start_candidate

    start_ts = snap_timestamp(available_timestamps, start_candidate, prefer="ceil")
    end_ts = snap_timestamp(available_timestamps, end_candidate, prefer="floor")
    return (start_ts, start_ts) if end_ts < start_ts else (start_ts, end_ts)
