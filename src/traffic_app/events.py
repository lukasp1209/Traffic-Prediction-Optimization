from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from .domain import CityEvent
from .streamlit_compat import cache_data
from .text_utils import canonicalize_text


@cache_data(show_spinner=False)
def load_city_event_reference(config_dir: str) -> Dict[str, List[CityEvent]]:
    config_path = Path(config_dir)
    if not config_path.exists():
        return {}

    event_map: Dict[str, List[CityEvent]] = {}
    for file_path in sorted(config_path.glob("*.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        city_name = str(payload.get("city", file_path.stem)).strip()
        events_payload = payload.get("events", [])
        if not city_name or not isinstance(events_payload, list):
            continue

        parsed_events: List[CityEvent] = []
        for item in events_payload:
            if not isinstance(item, dict):
                continue
            parsed_events.append(
                CityEvent(
                    city=city_name,
                    name=str(item.get("name", "Event")).strip() or "Event",
                    start=str(item.get("start", "")).strip(),
                    end=str(item.get("end", "")).strip(),
                    impact_level=float(item.get("impact_level", 1.0) or 1.0),
                    category=str(item.get("category", "general")).strip() or "general",
                )
            )
        event_map[canonicalize_text(city_name)] = parsed_events

    return event_map


def events_to_frame(events: List[CityEvent]) -> pd.DataFrame:
    if not events:
        return pd.DataFrame(columns=["name", "start", "end", "impact_level", "category"])
    return pd.DataFrame(
        [
            {
                "name": event.name,
                "start": event.start,
                "end": event.end,
                "impact_level": event.impact_level,
                "category": event.category,
            }
            for event in events
        ]
    )


def frame_to_events(city_name: str, frame: pd.DataFrame) -> List[CityEvent]:
    events: List[CityEvent] = []
    if frame.empty:
        return events

    for _, row in frame.iterrows():
        name = str(row.get("name", "")).strip()
        start = str(row.get("start", "")).strip()
        end = str(row.get("end", "")).strip()
        if not name or not start or not end:
            continue
        try:
            impact_level = float(row.get("impact_level", 1.0) or 1.0)
        except (TypeError, ValueError):
            impact_level = 1.0
        category = str(row.get("category", "general")).strip() or "general"
        events.append(CityEvent(city=city_name, name=name, start=start, end=end, impact_level=impact_level, category=category))
    return events


def build_event_frame_for_city(selected_city: str, event_reference: Dict[str, List[CityEvent]]) -> pd.DataFrame:
    city_key = canonicalize_text(selected_city)
    return events_to_frame(event_reference.get(city_key, []))


def apply_event_calendar(df: pd.DataFrame, selected_city: str, event_frame: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["is_event"] = data.get("is_event", 0)
    data["event_intensity"] = data.get("event_intensity", 0.0)
    data["event_name"] = data.get("event_name", "")

    if event_frame.empty:
        data["is_event"] = data["is_event"].fillna(0).astype(int)
        data["event_intensity"] = data["event_intensity"].fillna(0.0).astype(float)
        return data

    event_rows = frame_to_events(selected_city, event_frame)
    if not event_rows:
        data["is_event"] = data["is_event"].fillna(0).astype(int)
        data["event_intensity"] = data["event_intensity"].fillna(0.0).astype(float)
        return data

    for event in event_rows:
        start_ts = pd.to_datetime(event.start, errors="coerce")
        end_ts = pd.to_datetime(event.end, errors="coerce")
        if pd.isna(start_ts) or pd.isna(end_ts):
            continue
        mask = (data["ds"] >= start_ts) & (data["ds"] <= end_ts)
        data.loc[mask, "is_event"] = 1
        data.loc[mask, "event_intensity"] = data.loc[mask, "event_intensity"].clip(lower=float(event.impact_level))
        data.loc[mask, "event_name"] = event.name

    data["is_event"] = data["is_event"].fillna(0).astype(int)
    data["event_intensity"] = data["event_intensity"].fillna(0.0).astype(float)
    return data


def get_event_feature_values(timestamp: pd.Timestamp, selected_city: str, event_frame: pd.DataFrame) -> tuple[int, float]:
    event_rows = frame_to_events(selected_city, event_frame)
    for event in event_rows:
        start_ts = pd.to_datetime(event.start, errors="coerce")
        end_ts = pd.to_datetime(event.end, errors="coerce")
        if pd.isna(start_ts) or pd.isna(end_ts):
            continue
        if start_ts <= timestamp <= end_ts:
            return 1, float(event.impact_level)
    return 0, 0.0
