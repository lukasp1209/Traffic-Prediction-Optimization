from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Traffic Backend API"
    app_env: str = "development"
    database_url: str = "sqlite:///./traffic_backend.db"
    tomtom_api_key: str = ""
    tomtom_base_url: str = "https://api.tomtom.com"
    ticketmaster_api_key: str = ""
    ticketmaster_base_url: str = "https://app.ticketmaster.com/discovery/v2"
    default_bbox: str = Field(
        default="8.596,50.045,8.754,50.180",
        description="Bounding box in lon1,lat1,lon2,lat2 for TomTom queries.",
    )
    backend_api_token: str = ""


settings = Settings()
