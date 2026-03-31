from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from .config import NUMERIC_FEATURES
from .events import get_event_feature_values
from .streamlit_compat import cache_resource


@cache_resource(show_spinner=False)
def train_models(df: pd.DataFrame, split_ratio: float):
    X = df[NUMERIC_FEATURES].values
    y = df["y"].values
    timestamps = df["ds"].reset_index(drop=True)

    split_idx = int(len(df) * split_ratio)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    ts_test = timestamps.iloc[split_idx:]

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    models = {
        "Lineare Regression": LinearRegression(),
        "Ridge-Regression": Ridge(alpha=1.0),
        "Random Forest": RandomForestRegressor(n_estimators=120, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingRegressor(n_estimators=120, random_state=42),
    }

    metrics: List[Dict[str, float | str]] = []
    predictions: Dict[str, np.ndarray] = {}
    fitted_models: Dict[str, object] = {}

    for name, model in models.items():
        model.fit(X_train_sc, y_train)
        y_pred = model.predict(X_test_sc)
        predictions[name] = y_pred
        fitted_models[name] = model
        metrics.append(
            {
                "Algorithmus": name,
                "MAE": round(mean_absolute_error(y_test, y_pred), 3),
                "RMSE": round(np.sqrt(mean_squared_error(y_test, y_pred)), 3),
                "R2": round(r2_score(y_test, y_pred), 4),
            }
        )

    metrics_df = pd.DataFrame(metrics).sort_values("RMSE").reset_index(drop=True)
    y_test_series = pd.Series(y_test, index=ts_test)
    return metrics_df, predictions, y_test_series, ts_test, fitted_models, scaler


def make_recursive_forecast(
        model,
        scaler: StandardScaler,
        history: pd.DataFrame,
        horizon_hours: int,
        selected_city: str,
        event_frame: pd.DataFrame,
) -> pd.DataFrame:
    history = history.sort_values("ds").reset_index(drop=True)
    values = history["y"].astype(float).tolist()
    current_ts = history["ds"].max()
    rows: List[Dict[str, float | int | pd.Timestamp]] = []

    for _ in range(horizon_hours):
        current_ts += pd.Timedelta(hours=1)
        hour = int(current_ts.hour)
        weekday = int(current_ts.weekday())
        is_weekend = int(weekday >= 5)
        month = int(current_ts.month)
        is_event, event_intensity = get_event_feature_values(current_ts, selected_city, event_frame)

        lag1 = values[-1]
        lag24 = values[-24] if len(values) >= 24 else float(np.mean(values))
        rmean3 = float(np.mean(values[-3:]))
        rmean24 = float(np.mean(values[-24:]))

        features = np.array([[hour, weekday, is_weekend, month, lag1, lag24, rmean3, rmean24, is_event, event_intensity]])
        prediction = float(np.clip(model.predict(scaler.transform(features))[0], 0, None))
        values.append(prediction)
        rows.append(
            {
                "ds": current_ts,
                "base_forecast": prediction,
                "hour": hour,
                "is_event": is_event,
                "event_intensity": event_intensity,
            }
        )

    return pd.DataFrame(rows)
