from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from ..config import settings


class TicketmasterClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.api_key = api_key or settings.ticketmaster_api_key
        self.base_url = (base_url or settings.ticketmaster_base_url).rstrip("/")

    def _ensure_api_key(self) -> None:
        if not self.api_key:
            raise ValueError("Ticketmaster API key is not configured. Set TICKETMASTER_API_KEY.")

    def search_events(self, city: str, country_code: str = "DE", size: int = 50) -> dict[str, Any]:
        self._ensure_api_key()
        url = f"{self.base_url}/events.json"
        params = {
            "apikey": self.api_key,
            "city": city,
            "countryCode": country_code,
            "size": size,
            "sort": "date,asc",
        }
        response = httpx.get(url, params=params, timeout=20.0)
        response.raise_for_status()
        return {
            "fetched_at": datetime.utcnow(),
            "city": city,
            "payload": response.json(),
        }
