from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _resolve_default_data() -> Path:
    candidates = (
        PROJECT_ROOT / "data" / "traffic_darmstadt.csv",
        PROJECT_ROOT / "data" / "df_final.csv",
        PROJECT_ROOT / "data" / "traffic_darmstadt_streets.csv",
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


DEFAULT_DATA = _resolve_default_data()
CITY_CONFIG_DIR = PROJECT_ROOT / "data" / "city_streets"
EVENT_CONFIG_DIR = PROJECT_ROOT / "data" / "city_events"
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_API_URLS = (
    OVERPASS_API_URL,
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
)

NUMERIC_FEATURES = ["hour", "weekday", "is_weekend", "month", "lag1", "lag24", "rmean3", "rmean24", "is_event", "event_intensity"]
