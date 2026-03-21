from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import requests
import streamlit as st

from .config import NUMERIC_FEATURES
from .domain import CityStreetReference
from .text_utils import canonicalize_text


@st.cache_data(show_spinner=False)
def load_city_street_reference(config_dir: str) -> CityStreetReference:
    default_multipliers = {}

    config_path = Path(config_dir)
    if not config_path.exists():
        return CityStreetReference(weights={}, geometries={}, multipliers=default_multipliers)

    loaded_weights: Dict[str, Dict[str, float]] = {}
    loaded_geometries: Dict[str, Dict[str, List[List[float]]]] = {}
    loaded_multipliers: Dict[str, float] = {}

    for file_path in sorted(config_path.glob("*.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        city_name = str(payload.get("city", file_path.stem)).strip()
        streets_payload = payload.get("streets", [])
        if not city_name or not isinstance(streets_payload, list):
            continue

        city_weights: Dict[str, float] = {}
        city_geometries: Dict[str, List[List[float]]] = {}
        for street_payload in streets_payload:
            if not isinstance(street_payload, dict):
                continue

            street_name = str(street_payload.get("name", "")).strip()
            if not street_name:
                continue

            try:
                city_weights[street_name] = float(street_payload.get("weight", 0))
            except (TypeError, ValueError):
                city_weights[street_name] = 0.0

            geometry = street_payload.get("geometry")
            if isinstance(geometry, list) and len(geometry) >= 2:
                city_geometries[canonicalize_text(street_name)] = geometry

        if city_weights:
            loaded_weights[city_name] = city_weights
        if city_geometries:
            loaded_geometries[canonicalize_text(city_name)] = city_geometries

        try:
            loaded_multipliers[city_name] = float(payload.get("city_multiplier", 1.0))
        except (TypeError, ValueError):
            loaded_multipliers[city_name] = 1.0

    return CityStreetReference(
        weights=loaded_weights,
        geometries=loaded_geometries,
        multipliers=loaded_multipliers or default_multipliers,
    )


@st.cache_data(show_spinner=False)
def generate_synthetic_data(periods: int, seed: int) -> pd.DataFrame:
    np.random.seed(seed)
    ds = pd.date_range(start="2023-01-01", periods=periods, freq="h")

    hour = ds.hour.values
    weekday = ds.dayofweek.values
    weather_options = ["sunny", "cloudy", "rainy"]
    weather_raw = np.random.choice([0, 1, 2], size=periods, p=[0.5, 0.3, 0.2])
    weather = np.array(weather_options)[weather_raw]

    trend = np.linspace(0, 8, periods)
    seasonal_year = 5 * np.sin(2 * np.pi * (ds.dayofyear.values / 365 - 0.25))
    hour_effect = 28 * np.exp(-0.5 * ((hour - 8) / 1.5) ** 2) + 22 * np.exp(-0.5 * ((hour - 17) / 1.5) ** 2)
    weekend_effect = np.where(weekday >= 5, -18, 0)
    weather_effect = np.where(weather == "rainy", -12, np.where(weather == "sunny", 6, 0))

    np.random.seed(seed + 7)
    holiday_days = np.random.choice(np.arange(periods // 24), size=min(15, periods // 24), replace=False)
    holiday_mask = np.zeros(periods)
    for day_idx in holiday_days:
        holiday_mask[day_idx * 24: (day_idx + 1) * 24] = -20

    noise = np.random.normal(0, 6, periods)
    y = (50 + trend + seasonal_year + hour_effect + weekend_effect + weather_effect + holiday_mask + noise).clip(5, 120)
    df = pd.DataFrame({"ds": ds, "y": y.round(0).astype(int), "weather": weather})
    return engineer_features(df)


@st.cache_data(show_spinner=False)
def normalize_input(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data.columns = [str(column).strip() for column in data.columns]

    rename_map = {}
    for col in data.columns:
        low = col.lower().strip()
        if low in {"timestamp", "datetime", "zeit", "zeitpunkt"}:
            rename_map[col] = "ds"
        elif low in {"traffic", "count", "value", "verkehr", "aufkommen"}:
            rename_map[col] = "y"
        elif low in {"stadt"}:
            rename_map[col] = "city"
        elif low in {"strasse", "straÃŸe"}:
            rename_map[col] = "street"

    data = data.rename(columns=rename_map)

    if "timestamp" in data.columns and "ds" not in data.columns:
        data = data.rename(columns={"timestamp": "ds"})

    if "ds" not in data.columns:
        for col in data.columns:
            low = col.lower()
            if "date" in low or "time" in low:
                data = data.rename(columns={col: "ds"})
                break

    if "ds" not in data.columns:
        raise ValueError("Keine Zeitspalte gefunden. Erwartet: 'ds' oder 'timestamp'.")

    if "y" not in data.columns:
        numeric_cols = [col for col in data.select_dtypes(include=[np.number]).columns if col != "ds"]
        if not numeric_cols:
            raise ValueError("Keine Zielspalte gefunden. Erwartet: 'y' oder eine numerische Spalte.")
        data = data.rename(columns={numeric_cols[0]: "y"})

    data["ds"] = pd.to_datetime(data["ds"], errors="coerce")
    data["y"] = pd.to_numeric(data["y"], errors="coerce")

    if "city" in data.columns:
        data["city"] = data["city"].astype(str).str.strip()
    if "street" in data.columns:
        data["street"] = data["street"].astype(str).str.strip()

    return data.dropna(subset=["ds", "y"]).sort_values("ds").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["hour"] = data["ds"].dt.hour
    data["weekday"] = data["ds"].dt.weekday
    data["is_weekend"] = (data["weekday"] >= 5).astype(int)
    data["month"] = data["ds"].dt.month
    data["is_event"] = pd.to_numeric(data.get("is_event", 0), errors="coerce").fillna(0).astype(int)
    data["event_intensity"] = pd.to_numeric(data.get("event_intensity", 0.0), errors="coerce").fillna(0.0)

    data["lag1"] = data["lag_1"] if "lag1" not in data.columns and "lag_1" in data.columns else data.get("lag1", data["y"].shift(1))
    data["lag24"] = data["lag_24"] if "lag24" not in data.columns and "lag_24" in data.columns else data.get("lag24", data["y"].shift(24))
    data["rmean3"] = data["rolling_mean_3h"] if "rmean3" not in data.columns and "rolling_mean_3h" in data.columns else data.get("rmean3", data["y"].shift(1).rolling(3).mean())
    data["rmean24"] = data.get("rmean24", data["y"].shift(1).rolling(24).mean())

    return data.dropna(subset=NUMERIC_FEATURES + ["y"]).reset_index(drop=True)


def ensure_city_street_schema(df: pd.DataFrame, reference: CityStreetReference) -> pd.DataFrame:
    data = df.copy()

    if "city" in data.columns:
        data["city"] = data["city"].astype(str).str.strip()
    if "street" in data.columns:
        data["street"] = data["street"].astype(str).str.strip()

    if "city" not in data.columns and "street" not in data.columns:
        if not reference.weights:
            raise ValueError("Keine Demo-Stadtdaten gefunden. Erwartet JSON-Dateien unter data/city_streets.")

        parts: List[pd.DataFrame] = []
        for city, streets in reference.weights.items():
            for street, weight in streets.items():
                street_df = data.copy()
                street_df["city"] = city
                street_df["street"] = street
                peak_multiplier = np.where(street_df["ds"].dt.hour.isin([7, 8, 9, 16, 17, 18]), 1.08, 0.96)
                weekend_multiplier = np.where(street_df["ds"].dt.weekday >= 5, 0.9, 1.0)
                city_multiplier = reference.multipliers.get(city, 1.0)
                street_df["y"] = street_df["y"] * weight * peak_multiplier * weekend_multiplier * city_multiplier
                parts.append(street_df)

        if not parts:
            raise ValueError("Demo-Stadtdaten sind leer. Bitte JSON-Dateien unter data/city_streets pruefen.")

        expanded = pd.concat(parts, ignore_index=True)
        expanded["y"] = expanded["y"].clip(lower=0)
        return expanded

    if "city" not in data.columns:
        data["city"] = "Unbekannt"
    if "street" not in data.columns:
        data["street"] = "Gesamtnetz"

    return data.dropna(subset=["city", "street"])


def aggregate_city_series(df: pd.DataFrame, selected_city: str, selected_streets: List[str]) -> pd.DataFrame:
    filtered = df[(df["city"] == selected_city) & (df["street"].isin(selected_streets))].copy()
    if filtered.empty:
        return filtered
    return filtered.groupby("ds", as_index=False)["y"].sum().sort_values("ds").reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=60)
def fetch_live_traffic_records(api_url: str, bearer_token: str) -> pd.DataFrame:
    if not api_url.strip():
        return pd.DataFrame()

    headers = {"User-Agent": "traffic-prediction-optimization/1.0"}
    if bearer_token.strip():
        headers["Authorization"] = f"Bearer {bearer_token.strip()}"

    try:
        response = requests.get(api_url.strip(), headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return pd.DataFrame()

    records = payload.get("records", []) if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return pd.DataFrame()

    data = pd.DataFrame(records)
    if data.empty:
        return data

    rename_map = {}
    for col in data.columns:
        low = str(col).strip().lower()
        if low in {"timestamp", "datetime", "time", "zeit", "zeitpunkt"}:
            rename_map[col] = "ds"
        elif low in {"value", "count", "traffic", "flow", "y", "verkehr"}:
            rename_map[col] = "y"
        elif low in {"city", "stadt"}:
            rename_map[col] = "city"
        elif low in {"street", "strasse", "straÃŸe"}:
            rename_map[col] = "street"

    data = data.rename(columns=rename_map)
    if "ds" not in data.columns:
        data["ds"] = pd.Timestamp.utcnow()

    if not {"city", "street", "y", "ds"}.issubset(set(data.columns)):
        return pd.DataFrame()

    data["ds"] = pd.to_datetime(data["ds"], errors="coerce")
    data["y"] = pd.to_numeric(data["y"], errors="coerce")
    data["city"] = data["city"].astype(str).str.strip()
    data["street"] = data["street"].astype(str).str.strip()
    return data.dropna(subset=["ds", "y", "city", "street"]).reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=60)
def fetch_backend_traffic_records(api_url: str, api_token: str, bbox: str) -> pd.DataFrame:
    if not api_url.strip():
        return pd.DataFrame()

    headers = {"User-Agent": "traffic-prediction-optimization/1.0"}
    if api_token.strip():
        headers["x-api-token"] = api_token.strip()

    try:
        response = requests.get(
            f"{api_url.rstrip('/')}/traffic/incidents",
            params={"bbox": bbox},
            headers=headers,
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return pd.DataFrame()

    incidents = payload.get("incidents", [])
    rows = []
    fetched_at = pd.to_datetime(payload.get("fetched_at"), errors="coerce")
    for incident in incidents:
        properties = incident.get("properties", {})
        description = ""
        for event in properties.get("events", []):
            if event.get("description"):
                description = str(event["description"])
                break

        rows.append(
            {
                "ds": fetched_at if pd.notna(fetched_at) else pd.Timestamp.utcnow(),
                "y": float(properties.get("magnitudeOfDelay", 0) or 0),
                "city": "Backend API",
                "street": str(properties.get("from") or properties.get("to") or description or "Unbekannt"),
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)
