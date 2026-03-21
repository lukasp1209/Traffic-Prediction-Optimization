from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DATA = PROJECT_ROOT / "data" / "traffic_frankfurt.csv"
CITY_CONFIG_DIR = PROJECT_ROOT / "data" / "city_streets"
EVENT_CONFIG_DIR = PROJECT_ROOT / "data" / "city_events"
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

NUMERIC_FEATURES = ["hour", "weekday", "is_weekend", "month", "lag1", "lag24", "rmean3", "rmean24", "is_event", "event_intensity"]
