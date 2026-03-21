from __future__ import annotations

import json
from typing import Dict, List

import numpy as np
import pandas as pd
import streamlit as st

from .domain import SCENARIOS


def detect_congestion_alerts(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    alerts_df = df.copy()
    alerts_df["is_critical"] = alerts_df["base_forecast"] >= threshold
    return alerts_df[alerts_df["is_critical"]].copy()


def detect_anomalies(series: pd.Series, z_thresh: float = 3.0) -> pd.Series:
    std = float(series.std())
    if std == 0 or np.isnan(std):
        return pd.Series(False, index=series.index)
    z_scores = (series - float(series.mean())) / std
    return np.abs(z_scores) > z_thresh


def compute_measure_effects(measures: Dict[str, int]) -> float:
    weights = {
        "signal": 0.12,
        "public_transport": 0.10,
        "home_office": 0.08,
        "construction": 0.06,
    }
    effect = sum((measures[key] / 100.0) * weights[key] for key in weights)
    return min(effect, 0.4)


def optimize_traffic(forecast_df: pd.DataFrame, measures: Dict[str, int]) -> pd.DataFrame:
    df = forecast_df.copy()
    base_effect = compute_measure_effects(measures)
    peak_hours = {7, 8, 9, 16, 17, 18}
    df["hour_factor"] = df["hour"].apply(lambda hour: 1.3 if hour in peak_hours else 0.7)
    df["effective_reduction"] = np.clip(base_effect * df["hour_factor"], 0, 0.5)
    df["optimized"] = df["base_forecast"] * (1 - df["effective_reduction"])
    df["optimized_forecast"] = df["optimized"]
    return df


def compute_kpis(df: pd.DataFrame) -> Dict[str, float]:
    base = float(df["base_forecast"].sum())
    optimized = float(df["optimized"].sum())
    reduction = ((base - optimized) / base * 100) if base else 0.0
    return {
        "baseline": base,
        "optimized": optimized,
        "reduction_pct": reduction,
        "baseline_total": base,
        "optimized_total": optimized,
    }


def build_optimization_plan(forecast_df: pd.DataFrame, target_reduction_pct: float, measures: Dict[str, int]):
    df = optimize_traffic(forecast_df, measures)
    kpis = compute_kpis(df)
    reduction_pct = kpis["reduction_pct"]
    return df, {
        "baseline_total": kpis["baseline_total"],
        "optimized_total": kpis["optimized_total"],
        "reduction_pct": reduction_pct,
        "achieved": reduction_pct >= target_reduction_pct,
        "gap": max(target_reduction_pct - reduction_pct, 0.0),
    }


def get_selected_measures() -> Dict[str, int]:
    scenario_name = st.selectbox("Scenario Preset", list(SCENARIOS.keys()), index=1)
    scenario = SCENARIOS[scenario_name]

    st.caption(f"Ausgewaehltes Preset: {scenario.name}")
    signal = st.slider("Ampelsteuerung", 0, 100, scenario.signal, 5)
    pt = st.slider("OePNV-Verstaerkung", 0, 100, scenario.public_transport, 5)
    home = st.slider("Homeoffice-Anreiz", 0, 100, scenario.home_office, 5)
    construction = st.slider("Baustellen-Taktung", 0, 100, scenario.construction, 5)
    return {
        "signal": signal,
        "public_transport": pt,
        "home_office": home,
        "construction": construction,
    }


def run_api_mode(
        forecast_df: pd.DataFrame,
        optimized_df: pd.DataFrame,
        kpis: Dict[str, float],
        alerts_df: pd.DataFrame,
        anomalies_df: pd.DataFrame,
        selected_city: str,
        selected_streets: List[str],
        measures: Dict[str, int],
        threshold: float,
) -> str:
    payload = {
        "city": selected_city,
        "streets": selected_streets,
        "threshold": threshold,
        "measures": measures,
        "kpis": kpis,
        "forecast": forecast_df.tail(24).to_dict(orient="records"),
        "optimized_forecast": optimized_df.tail(24)[["ds", "base_forecast", "optimized_forecast", "effective_reduction"]].to_dict(orient="records"),
        "alerts": alerts_df.to_dict(orient="records"),
        "anomalies": anomalies_df.to_dict(orient="records"),
    }
    return json.dumps(payload, default=str)
