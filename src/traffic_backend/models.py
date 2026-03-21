from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class TrafficFlowSnapshot(Base):
    __tablename__ = "traffic_flow_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default="tomtom", index=True)
    location_label: Mapped[str] = mapped_column(String(128), default="default-area", index=True)
    free_flow_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_travel_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_flow_travel_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    road_closure: Mapped[bool | None] = mapped_column(nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class TrafficIncidentSnapshot(Base):
    __tablename__ = "traffic_incident_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default="tomtom", index=True)
    incident_id: Mapped[str] = mapped_column(String(128), index=True)
    icon_category: Mapped[int | None] = mapped_column(Integer, nullable=True)
    magnitude_of_delay: Mapped[int | None] = mapped_column(Integer, nullable=True)
    from_desc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    to_desc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    geometry_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_payload: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ImportedCityEvent(Base):
    __tablename__ = "imported_city_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(32), default="ticketmaster", index=True)
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    city: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    venue_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    impact_level: Mapped[float] = mapped_column(Float, default=1.0)
    raw_payload: Mapped[str] = mapped_column(Text)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
