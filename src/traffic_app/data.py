from __future__ import annotations

import csv
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Dict, List
from zipfile import ZipFile

import numpy as np
import pandas as pd
from .config import NUMERIC_FEATURES
from .domain import CityStreetReference
from .streamlit_compat import cache_data
from .text_utils import canonicalize_text


@cache_data(show_spinner=False)
def read_csv_file(path: str) -> pd.DataFrame:
    return pd.read_csv(path)


@cache_data(show_spinner=False)
def read_csv_bytes(payload: bytes) -> pd.DataFrame:
    return pd.read_csv(BytesIO(payload))


def _read_delimited_bytes(payload: bytes) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            sample = payload[:4096].decode(encoding)
        except UnicodeDecodeError:
            continue

        delimiter = None
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=";,\t").delimiter
        except csv.Error:
            delimiter = None

        try:
            if delimiter is not None:
                return pd.read_csv(BytesIO(payload), sep=delimiter, encoding=encoding)
            return pd.read_csv(BytesIO(payload), sep=None, engine="python", encoding=encoding)
        except Exception:
            continue

    return pd.read_csv(BytesIO(payload))


def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    cleaned.columns = [str(column).replace("\ufeff", "").strip() for column in cleaned.columns]
    return cleaned


def _extract_open_traffic_timestamp(df: pd.DataFrame) -> pd.Series:
    data = _clean_columns(df)
    normalized_names = {column: canonicalize_text(str(column)).replace(" ", "") for column in data.columns}
    preferred_candidates = [
        "intervallbeginn(lokalzeit)",
        "ds",
        "timestamp",
        "datetime",
        "zeitpunkt",
        "datumzeit",
        "datetimeutc",
        "intervallbeginn(utc)",
    ]

    for candidate in preferred_candidates:
        for column, normalized in normalized_names.items():
            if normalized != candidate:
                continue
            parsed = pd.to_datetime(data[column], errors="coerce", dayfirst=True)
            if parsed.notna().any():
                return parsed

    date_column = None
    time_column = None
    for column, normalized in normalized_names.items():
        if date_column is None and "datum" in normalized:
            date_column = column
        if date_column is None and normalized == "date":
            date_column = column
        if time_column is None and normalized in {"uhrzeit", "zeit", "time"}:
            time_column = column

    if date_column and time_column:
        combined = pd.to_datetime(
            data[date_column].astype(str).str.strip() + " " + data[time_column].astype(str).str.strip(),
            errors="coerce",
            dayfirst=True,
        )
        if combined.notna().any():
            return combined

    for column in data.columns[:3]:
        parsed = pd.to_datetime(data[column], errors="coerce", dayfirst=True)
        if parsed.notna().mean() >= 0.7:
            return parsed

    return pd.Series(pd.NaT, index=data.index, dtype="datetime64[ns]")


def _detect_open_traffic_measurements(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    measurements: list[tuple[str, str, str]] = []

    for column in df.columns:
        label = str(column).strip()
        if "(Belegungen/Intervall)" in label:
            sensor_id = label.split("(", 1)[0].strip()
            measurements.append((column, sensor_id, "count"))
            continue
        if "(Verweilzeit/Intervall)" in label:
            sensor_id = label.split("(", 1)[0].strip()
            measurements.append((column, sensor_id, "dwell_time"))
            continue

        compact = re.sub(r"[^A-Za-z0-9]", "", label).upper()
        match = re.match(r"^(D\d+)([A-Z])$", compact)
        if not match:
            continue

        sensor_id, suffix = match.groups()
        metric = "count" if suffix == "Z" else "occupancy" if suffix == "B" else "value"
        measurements.append((column, sensor_id, metric))

    if measurements:
        count_measurements = [item for item in measurements if item[2] == "count"]
        return count_measurements or measurements

    fallback_columns = [column for column in df.select_dtypes(include=[np.number]).columns]
    return [(column, canonicalize_text(str(column)).upper(), "value") for column in fallback_columns]


@cache_data(show_spinner=False)
def read_open_traffic_zip_bytes(payload: bytes, city_name: str = "Darmstadt", intersection_name: str = "") -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    zip_label = Path(intersection_name or "OpenTrafficData").stem

    with ZipFile(BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not members:
            raise ValueError("Die ZIP-Datei enthält keine CSV-Dateien.")

        for member in sorted(members):
            raw_bytes = archive.read(member)
            month_df = _clean_columns(_read_delimited_bytes(raw_bytes))
            if month_df.empty:
                continue

            timestamps = _extract_open_traffic_timestamp(month_df)
            if timestamps.notna().sum() == 0:
                continue

            measurement_columns = _detect_open_traffic_measurements(month_df)
            if not measurement_columns:
                continue

            for column, sensor_id, metric in measurement_columns:
                values = pd.to_numeric(month_df[column], errors="coerce")
                if values.notna().sum() == 0:
                    continue

                source_name = Path(member).stem
                sensor_label = f"{zip_label} - {sensor_id}{'Z' if metric == 'count' else 'B' if metric == 'occupancy' else ''}"
                sensor_df = pd.DataFrame(
                    {
                        "ds": timestamps,
                        "y": values,
                        "city": city_name,
                        "street": sensor_label,
                        "sensor_id": sensor_id,
                        "metric": metric,
                        "source_file": source_name,
                    }
                ).dropna(subset=["ds", "y"])
                if sensor_df.empty:
                    continue

                sensor_df["ds"] = sensor_df["ds"].dt.floor("h")
                agg_fn = "sum" if metric == "count" else "mean"
                hourly_df = (
                    sensor_df.groupby(["ds", "city", "street", "sensor_id", "metric"], as_index=False)
                    .agg(y=("y", agg_fn))
                    .sort_values("ds")
                )
                frames.append(hourly_df)

    if not frames:
        raise ValueError("Aus der ZIP-Datei konnten keine gültigen Zeitreihen gelesen werden.")

    combined = pd.concat(frames, ignore_index=True)
    combined["y"] = pd.to_numeric(combined["y"], errors="coerce")
    combined["city"] = combined["city"].astype(str).str.strip()
    combined["street"] = combined["street"].astype(str).str.strip()
    combined = combined.dropna(subset=["ds", "y", "city", "street"])
    if combined.empty:
        raise ValueError("Die gelesenen ZIP-Daten enthalten keine verwendbaren Werte.")
    return combined.sort_values(["street", "ds"]).reset_index(drop=True)


@cache_data(show_spinner=False)
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


@cache_data(show_spinner=False)
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


@cache_data(show_spinner=False)
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
        elif low in {"strasse", "straße"}:
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


@cache_data(show_spinner=False)
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
            raise ValueError("Demo-Stadtdaten sind leer. Bitte JSON-Dateien unter data/city_streets prüfen.")

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
