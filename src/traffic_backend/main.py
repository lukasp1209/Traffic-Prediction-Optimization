from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy.orm import Session

from .config import settings
from .db import Base, engine, get_db
from .schemas import (
    CityEventItem,
    CityEventListResponse,
    EventImportSummary,
    FlowResponse,
    HealthResponse,
    IncidentResponse,
    IngestionSummary,
)
from .services.repository import list_imported_events, store_flow_snapshot, store_incident_snapshots, store_ticketmaster_events
from .services.ticketmaster import TicketmasterClient
from .services.tomtom import TomTomClient

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name, version="0.1.0")


def require_token(x_api_token: Annotated[str | None, Header()] = None) -> None:
    if settings.backend_api_token and x_api_token != settings.backend_api_token:
        raise HTTPException(status_code=401, detail="Invalid API token.")


@app.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.app_env)


@app.get("/traffic/flow", response_model=FlowResponse, dependencies=[Depends(require_token)])
def get_flow(
        point: str = Query(default="50.1109,8.6821", description="lat,lon"),
        location: str = Query(default="frankfurt-center"),
) -> FlowResponse:
    client = TomTomClient()
    result = client.fetch_flow_segment_data(point=point)
    return FlowResponse(
        source="tomtom",
        location=location,
        fetched_at=result["fetched_at"],
        data=result["payload"],
    )


@app.get("/traffic/incidents", response_model=IncidentResponse, dependencies=[Depends(require_token)])
def get_incidents(
        bbox: str = Query(default=settings.default_bbox),
        time_validity_filter: str = Query(default="present"),
) -> IncidentResponse:
    client = TomTomClient()
    result = client.fetch_incidents(bbox=bbox, time_validity_filter=time_validity_filter)
    payload = result["payload"]
    incidents = payload.get("incidents", [])
    return IncidentResponse(
        source="tomtom",
        bbox=bbox,
        fetched_at=result["fetched_at"],
        total=len(incidents),
        incidents=incidents,
    )


@app.post("/ingestion/snapshot", response_model=IngestionSummary, dependencies=[Depends(require_token)])
def ingest_snapshot(
        point: str = Query(default="50.1109,8.6821"),
        location: str = Query(default="frankfurt-center"),
        bbox: str = Query(default=settings.default_bbox),
        db: Session = Depends(get_db),
) -> IngestionSummary:
    client = TomTomClient()
    flow_result = client.fetch_flow_segment_data(point=point)
    incident_result = client.fetch_incidents(bbox=bbox)

    stored_flow_rows = store_flow_snapshot(db, flow_result["payload"], location_label=location)
    stored_incident_rows = store_incident_snapshots(db, incident_result["payload"])

    return IngestionSummary(
        stored_flow_rows=stored_flow_rows,
        stored_incident_rows=stored_incident_rows,
        fetched_at=datetime.utcnow(),
    )


@app.post("/events/import/ticketmaster", response_model=EventImportSummary, dependencies=[Depends(require_token)])
def import_ticketmaster_events(
        city: str = Query(..., min_length=2),
        country_code: str = Query(default="DE"),
        size: int = Query(default=50, ge=1, le=200),
        db: Session = Depends(get_db),
) -> EventImportSummary:
    client = TicketmasterClient()
    result = client.search_events(city=city, country_code=country_code, size=size)
    imported_rows = store_ticketmaster_events(db, city=city, payload=result["payload"])
    return EventImportSummary(
        city=city,
        source="ticketmaster",
        imported_rows=imported_rows,
        fetched_at=result["fetched_at"],
    )


@app.get("/events", response_model=CityEventListResponse, dependencies=[Depends(require_token)])
def get_city_events(city: str = Query(..., min_length=2), db: Session = Depends(get_db)) -> CityEventListResponse:
    rows = list_imported_events(db, city=city)
    events = [
        CityEventItem(
            source=row.source,
            external_id=row.external_id,
            city=row.city,
            name=row.name,
            category=row.category,
            venue_name=row.venue_name,
            start_at=row.start_at,
            end_at=row.end_at,
            impact_level=row.impact_level,
        )
        for row in rows
    ]
    return CityEventListResponse(city=city, total=len(events), events=events)
