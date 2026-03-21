from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TrafficScenario:
    name: str
    signal: int
    public_transport: int
    home_office: int
    construction: int


@dataclass(frozen=True)
class CityStreetReference:
    weights: Dict[str, Dict[str, float]]
    geometries: Dict[str, Dict[str, List[List[float]]]]
    multipliers: Dict[str, float]


@dataclass(frozen=True)
class CityEvent:
    city: str
    name: str
    start: str
    end: str
    impact_level: float
    category: str = "general"


SCENARIOS = {
    "Aggressive Peak Reduction": TrafficScenario("Aggressive Peak Reduction", 80, 70, 60, 40),
    "Balanced Strategy": TrafficScenario("Balanced Strategy", 60, 50, 40, 30),
    "Low Intervention": TrafficScenario("Low Intervention", 30, 30, 20, 20),
}
