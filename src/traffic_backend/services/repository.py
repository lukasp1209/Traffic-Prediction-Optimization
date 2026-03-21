from __future__ import annotations

import datetime
import json
from typing import Any

from sqlalchemy.orm import Session

from ..models import TrafficFlowSnapshot, TrafficIncidentSnapshot
from ..models import ImportedCityEvent


def store_flow_snapshot(db: Session, payload: dict[str, Any], location_label: str) -> int:
    segment = payload.get("flowSegmentData", {})
    row = TrafficFlowSnapshot(
        location_label=location_label,
        free_flow_speed=segment.get("freeFlowSpeed"),
        current_speed=segment.get("currentSpeed"),
        current_travel_time=segment.get("currentTravelTime"),
        free_flow_travel_time=segment.get("freeFlowTravelTime"),
        confidence=segment.get("confidence"),
        road_closure=segment.get("roadClosure"),
        raw_payload=json.dumps(payload, default=str),
    )
    db.add(row)
    db.commit()
    return 1


def store_incident_snapshots(db: Session, payload: dict[str, Any]) -> int:
    incidents = payload.get("incidents", [])
    rows = 0
    for incident in incidents:
        properties = incident.get("properties", {})
        geometry = incident.get("geometry", {})
        events = properties.get("events", [])
        description = "; ".join(str(event.get("description", "")).strip() for event in events if event.get("description"))
        row = TrafficIncidentSnapshot(
            incident_id=str(properties.get("id", "")),
            icon_category=properties.get("iconCategory"),
            magnitude_of_delay=properties.get("magnitudeOfDelay"),
            from_desc=properties.get("from"),
            to_desc=properties.get("to"),
            description=description or None,
            geometry_type=geometry.get("type"),
            raw_payload=json.dumps(incident, default=str),
        )
        db.add(row)
        rows += 1

    db.commit()
    return rows


def store_ticketmaster_events(db: Session, city: str, payload: dict[str, Any]) -> int:
    embedded = payload.get("_embedded", {})
    events = embedded.get("events", [])
    rows = 0

    for event in events:
        classifications = event.get("classifications", [])
        category = None
        if classifications:
            category = (
                classifications[0].get("segment", {}).get("name")
                or classifications[0].get("genre", {}).get("name")
            )

        venues = event.get("_embedded", {}).get("venues", [])
        venue_name = venues[0].get("name") if venues else None

        start_at = event.get("dates", {}).get("start", {}).get("dateTime")
        end_at = event.get("dates", {}).get("end", {}).get("dateTime")

        row = ImportedCityEvent(
            source="ticketmaster",
            external_id=str(event.get("id", "")),
            city=city,
            name=str(event.get("name", "Event")),
            category=category,
            venue_name=venue_name,
            start_at=_to_datetime(start_at),
            end_at=_to_datetime(end_at),
            impact_level=_infer_impact_level(category, event),
            raw_payload=json.dumps(event, default=str),
        )
        db.add(row)
        rows += 1

    db.commit()
    return rows


def list_imported_events(db: Session, city: str) -> list[ImportedCityEvent]:
    return (
        db.query(ImportedCityEvent)
        .filter(ImportedCityEvent.city == city)
        .order_by(ImportedCityEvent.start_at.asc())
        .all()
    )


def _to_datetime(value: Any):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _infer_impact_level(category: str | None, event: dict[str, Any]) -> float:
    score = 1.2
    name = str(event.get("name", "")).lower()
    if category:
        normalized = category.lower()
        if "sports" in normalized:
            score = 3.0
        elif "music" in normalized:
            score = 2.4
        elif "arts" in normalized:
            score = 1.8

    if "stadion" in name or "arena" in name:
        score += 0.6
    return round(min(score, 5.0), 1)
