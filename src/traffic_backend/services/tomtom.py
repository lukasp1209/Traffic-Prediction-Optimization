from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from ..config import settings


class TomTomClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or settings.tomtom_api_key
        self.base_url = (base_url or settings.tomtom_base_url).rstrip("/")

    def _ensure_api_key(self) -> None:
        if not self.api_key:
            raise ValueError("TomTom API key is not configured. Set TOMTOM_API_KEY.")

    def fetch_flow_segment_data(self, point: str) -> dict[str, Any]:
        self._ensure_api_key()
        url = f"{self.base_url}/traffic/services/4/flowSegmentData/absolute/10/json"
        response = httpx.get(url, params={"key": self.api_key, "point": point}, timeout=20.0)
        response.raise_for_status()
        return {
            "fetched_at": datetime.utcnow(),
            "point": point,
            "payload": response.json(),
        }

    def fetch_incidents(self, bbox: str, time_validity_filter: str = "present") -> dict[str, Any]:
        self._ensure_api_key()
        url = f"{self.base_url}/traffic/services/5/incidentDetails"
        params = {
            "key": self.api_key,
            "bbox": bbox,
            "fields": "{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,events{description,code},from,to}}}",
            "language": "de-DE",
            "timeValidityFilter": time_validity_filter,
        }
        response = httpx.get(url, params=params, timeout=20.0)
        response.raise_for_status()
        return {
            "fetched_at": datetime.utcnow(),
            "bbox": bbox,
            "payload": response.json(),
        }
