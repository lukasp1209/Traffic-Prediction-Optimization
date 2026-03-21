from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str


class FlowResponse(BaseModel):
    source: str
    location: str
    fetched_at: datetime
    data: dict[str, Any]


class IncidentResponse(BaseModel):
    source: str
    bbox: str
    fetched_at: datetime
    total: int
    incidents: list[dict[str, Any]]


class IngestionSummary(BaseModel):
    stored_flow_rows: int
    stored_incident_rows: int
    fetched_at: datetime


class CityEventItem(BaseModel):
    source: str
    external_id: str
    city: str
    name: str
    category: str | None
    venue_name: str | None
    start_at: datetime | None
    end_at: datetime | None
    impact_level: float


class CityEventListResponse(BaseModel):
    city: str
    total: int
    events: list[CityEventItem]


class EventImportSummary(BaseModel):
    city: str
    source: str
    imported_rows: int
    fetched_at: datetime
