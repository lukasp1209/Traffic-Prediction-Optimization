from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from .config import CITY_CONFIG_DIR, DEFAULT_DATA, EVENT_CONFIG_DIR
from .data import (
    engineer_features,
    ensure_city_street_schema,
    fetch_backend_traffic_records,
    fetch_live_traffic_records,
    load_city_street_reference,
    normalize_input,
)
from .forecasting import make_recursive_forecast, train_models
from .events import (
    apply_event_calendar,
    build_event_frame_for_city,
    fetch_backend_events,
    import_ticketmaster_events,
    load_city_event_reference,
)
from .optimization import build_optimization_plan, detect_anomalies, detect_congestion_alerts, get_selected_measures, run_api_mode
from .ui import (
    configure_page,
    render_app_header,
    render_data_tab,
    render_model_tab,
    render_ops_tab,
    render_top_navigation,
)


def load_primary_data(source: str, uploaded, live_api_url: str, live_api_token: str) -> pd.DataFrame:
    if source == "Frankfurt Testdatensatz":
        if not DEFAULT_DATA.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {DEFAULT_DATA}")
        return pd.read_csv(DEFAULT_DATA)
    if source == "CSV-Import":
        if uploaded is None:
            raise ValueError("Bitte eine CSV-Datei hochladen.")
        return pd.read_csv(uploaded)
    live_df = fetch_live_traffic_records(live_api_url, live_api_token)
    if live_df.empty:
        raise ValueError("Die Live JSON API liefert keine gueltigen Daten.")
    return live_df

def load_map_traffic_data(
        map_data_source: str,
        map_uploaded_csv,
        city_street_df: pd.DataFrame,
        live_api_url: str,
        live_api_token: str,
        backend_api_url: str,
        backend_api_token: str,
        backend_bbox: str,
        reference,
) -> pd.DataFrame:
    map_traffic_df = city_street_df.copy()
    if map_data_source == "Historische CSV":
        if map_uploaded_csv is None:
            st.warning("Kartenquelle 'Historische CSV' aktiv, aber keine Datei hochgeladen. Es wird der Datensatz verwendet.")
            return map_traffic_df
        try:
            map_raw = pd.read_csv(map_uploaded_csv)
            return ensure_city_street_schema(normalize_input(map_raw), reference)
        except Exception as exc:
            st.warning(f"Historische CSV konnte nicht geladen werden ({exc}). Es wird der Datensatz verwendet.")
            return city_street_df.copy()

    if map_data_source == "Live JSON API":
        live_df = fetch_live_traffic_records(live_api_url, live_api_token)
        if live_df.empty:
            st.warning("Live JSON API liefert aktuell keine gueltigen Daten. Es wird der Datensatz verwendet.")
            return map_traffic_df
        return live_df.copy()

    if map_data_source == "FastAPI Backend":
        backend_df = fetch_backend_traffic_records(backend_api_url, backend_api_token, backend_bbox)
        if backend_df.empty:
            st.warning("FastAPI Backend liefert aktuell keine gueltigen Incident-Daten. Es wird der Datensatz verwendet.")
            return map_traffic_df
        return backend_df.copy()

    return map_traffic_df


def run_app() -> None:
    configure_page()

    reference = load_city_street_reference(str(CITY_CONFIG_DIR))
    event_reference = load_city_event_reference(str(EVENT_CONFIG_DIR))

    uploaded = None
    map_uploaded_csv = None
    live_api_url = ""
    live_api_token = ""
    backend_api_url = ""
    backend_api_token = ""
    backend_bbox = "8.596,50.045,8.754,50.180"

    with st.sidebar:
        st.markdown("## Steuerung")
        with st.expander("App-Modus & Daten", expanded=True):
            app_mode = st.selectbox("Modus", ("Dashboard", "API"))
            source = st.radio("Datenquelle", ("Frankfurt Testdatensatz", "CSV-Import", "Live JSON API"))
            split_ratio = st.slider("Train-Anteil", min_value=0.6, max_value=0.9, value=0.8, step=0.05)

            if source == "CSV-Import":
                uploaded = st.file_uploader("CSV-Datei hochladen", type=["csv"])
            elif source == "Live JSON API":
                live_api_url = st.text_input("Live-API URL", value="")
                live_api_token = st.text_input("Bearer Token (optional)", value="", type="password")

    try:
        raw_df = load_primary_data(source, uploaded, live_api_url, live_api_token)
    except ValueError as exc:
        st.info(str(exc))
        st.stop()
    except Exception as exc:
        st.error(f"Fehler beim Laden der Daten: {exc}")
        st.stop()

    try:
        normalized_df = normalize_input(raw_df)
        uses_demo_city_streets = source == "Frankfurt Testdatensatz" and "city" not in normalized_df.columns and "street" not in normalized_df.columns
        if source != "Frankfurt Testdatensatz" and not {"city", "street"}.issubset(set(normalized_df.columns)):
            st.error("Neue Staedte muessen per CSV oder API mit den Spalten city, street, ds und y geliefert werden.")
            st.stop()
        city_street_df = ensure_city_street_schema(normalized_df, reference) if uses_demo_city_streets else normalized_df.copy()
    except Exception as exc:
        st.error(str(exc))
        st.stop()

    if uses_demo_city_streets:
        st.info(
            "Hinweis: Die aktuelle Datei enthaelt keine city/street-Spalten. "
            "Die App verwendet deshalb ein Demo-Strassennetz aus JSON-Dateien unter data/city_streets."
        )

    with st.sidebar:
        with st.expander("Raumbezug", expanded=True):
            dataset_city_options = sorted(city_street_df["city"].dropna().unique().tolist())
            selector_options = dataset_city_options + ["Andere Stadt in Deutschland..."]
            city_choice = st.selectbox("Stadt", selector_options, index=0 if dataset_city_options else len(selector_options) - 1)

            if city_choice == "Andere Stadt in Deutschland...":
                selected_city = st.text_input("Beliebige Stadt in Deutschland", value="Berlin").strip() or "Berlin"
            else:
                selected_city = city_choice

            street_options = sorted(
                city_street_df.loc[city_street_df["city"] == selected_city, "street"].dropna().unique().tolist()
            )
            if street_options:
                selected_streets = st.multiselect("Strassenfilter fuer Karte", options=street_options, default=[])
                st.caption("Keine Auswahl bedeutet: alle darstellbaren Strassen der Stadt auf der Karte anzeigen.")
            else:
                st.caption("Keine lokalen Strassendaten fuer diese Stadt im Datensatz. Fuer die Karte werden OSM-Strassen verwendet.")
                selected_streets = []

        with st.expander("Kartenquelle", expanded=False):
            map_data_source = st.selectbox(
                "Auslastungsdaten",
                ("Primaerdatensatz", "Historische CSV", "Live JSON API", "FastAPI Backend"),
            )
            include_all_city_streets = st.checkbox("Alle OSM-Strassen der Stadt anzeigen", value=False)
            max_map_streets = st.slider("Max. Strassen auf Karte", min_value=100, max_value=2000, value=600, step=100)

            if map_data_source == "Historische CSV":
                map_uploaded_csv = st.file_uploader("Historische Verkehrs-CSV (city, street, ds, y)", type=["csv"], key="map_hist_csv")
            elif map_data_source == "Live JSON API":
                live_api_url = st.text_input("Live-API URL", value="")
                live_api_token = st.text_input("Bearer Token (optional)", value="", type="password")
            elif map_data_source == "FastAPI Backend":
                backend_api_url = st.text_input("Backend URL", value="http://localhost:8000")
                backend_api_token = st.text_input("Backend API Token (optional)", value="", type="password")
                backend_bbox = st.text_input("BBox", value=backend_bbox)

        with st.expander("Optimierung", expanded=False):
            target_reduction = st.slider("Ziel: Reduktion Verkehrsaufkommen (%)", 1, 30, 12)
            measures = get_selected_measures()

        with st.expander("Event-Kalender", expanded=False):
            st.caption("Events werden als zusaetzliche Einflussgroesse im Datensatz und Forecast beruecksichtigt.")
            import_col, sync_col = st.columns(2)
            with import_col:
                if st.button("Ticketmaster importieren", use_container_width=True):
                    if import_ticketmaster_events(
                            api_url=backend_api_url or "http://localhost:8000",
                            api_token=backend_api_token,
                            city=selected_city,
                    ):
                        st.success("Events wurden aus Ticketmaster importiert.")
                    else:
                        st.warning("Ticketmaster-Import fehlgeschlagen. Bitte Backend/API-Key pruefen.")
            with sync_col:
                load_backend_events = st.checkbox("Backend-Events laden", value=True)

            default_event_frame = build_event_frame_for_city(selected_city, event_reference)
            if load_backend_events:
                backend_event_frame = fetch_backend_events(
                    api_url=backend_api_url or "http://localhost:8000",
                    api_token=backend_api_token,
                    city=selected_city,
                )
                if not backend_event_frame.empty:
                    default_event_frame = (
                        pd.concat([default_event_frame, backend_event_frame], ignore_index=True)
                        .drop_duplicates(subset=["name", "start", "end"], keep="first")
                    )
            editor_key = f"event_calendar_editor_{selected_city}"
            event_frame = st.data_editor(
                default_event_frame,
                key=editor_key,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
                column_config={
                    "name": st.column_config.TextColumn("Event"),
                    "start": st.column_config.TextColumn("Start (z. B. 2026-05-01 18:00)"),
                    "end": st.column_config.TextColumn("Ende (z. B. 2026-05-01 23:00)"),
                    "impact_level": st.column_config.NumberColumn("Impact", min_value=0.0, max_value=5.0, step=0.1),
                    "category": st.column_config.SelectboxColumn(
                        "Kategorie",
                        options=["general", "concert", "football", "festival", "construction", "fair"],
                    ),
                },
            )

    selected_city_df = (
        city_street_df[city_street_df["city"] == selected_city]
        .groupby("ds", as_index=False)["y"]
        .sum()
        .sort_values("ds")
        .reset_index(drop=True)
    )
    if selected_city_df.empty:
        st.error("Fuer die ausgewaehlte Stadt liegen keine historischen Forecast-Daten vor. Bitte CSV- oder API-Daten fuer diese Stadt laden.")
        st.stop()

    map_traffic_df = load_map_traffic_data(
        map_data_source=map_data_source,
        map_uploaded_csv=map_uploaded_csv,
        city_street_df=city_street_df,
        live_api_url=live_api_url,
        live_api_token=live_api_token,
        backend_api_url=backend_api_url,
        backend_api_token=backend_api_token,
        backend_bbox=backend_bbox,
        reference=reference,
    )

    street_level_selected_df = map_traffic_df[map_traffic_df["city"] == selected_city].copy()
    if not include_all_city_streets and selected_streets:
        street_level_selected_df = street_level_selected_df[street_level_selected_df["street"].isin(selected_streets)].copy()

    available_timestamps = pd.to_datetime(street_level_selected_df["ds"], errors="coerce").dropna().sort_values().drop_duplicates().tolist()
    if not available_timestamps:
        fallback_now = pd.Timestamp.utcnow().tz_localize(None)
        available_timestamps = [fallback_now, fallback_now]
        st.warning("Keine gueltigen Zeitstempel fuer die Kartenquelle gefunden. Es wird ein aktueller Zeitpunkt verwendet.")

    selected_city_df = apply_event_calendar(selected_city_df, selected_city, event_frame)
    model_df = engineer_features(selected_city_df)
    if len(model_df) < 200:
        st.error("Zu wenige Datenpunkte nach Feature Engineering. Mindestens 200 erforderlich.")
        st.stop()

    metrics_df, predictions, y_test, ts_test, fitted_models, scaler = train_models(model_df, split_ratio)
    best_model_name = str(metrics_df.iloc[0]["Algorithmus"])
    best_model = fitted_models[best_model_name]

    horizon = st.slider("Planungshorizont (Stunden)", 6, 168, 48, 6)
    forecast_df = make_recursive_forecast(
        best_model,
        scaler,
        model_df[["ds", "y"]],
        horizon_hours=horizon,
        selected_city=selected_city,
        event_frame=event_frame,
    )
    threshold = float(forecast_df["base_forecast"].quantile(0.75))
    alerts_df = detect_congestion_alerts(forecast_df, threshold)
    anomalies_df = forecast_df[detect_anomalies(forecast_df["base_forecast"])].copy()
    optimized_df, kpis = build_optimization_plan(forecast_df, float(target_reduction), measures)

    if app_mode == "API":
        st.title("Traffic Decision Intelligence API")
        st.caption("Strukturierte Ausgabe fuer Integrationen und Downstream-Systeme")
        st.json(
            json.loads(
                run_api_mode(
                    forecast_df=forecast_df,
                    optimized_df=optimized_df,
                    kpis=kpis,
                    alerts_df=alerts_df,
                    anomalies_df=anomalies_df,
                    selected_city=selected_city,
                    selected_streets=selected_streets,
                    measures=measures,
                    threshold=threshold,
                )
            )
        )
        return

    render_app_header(selected_city, map_data_source, best_model_name, app_mode)
    selected_view = render_top_navigation()

    if selected_view == "Leitstelle":
        render_ops_tab(
            city_street_df=city_street_df,
            map_traffic_df=map_traffic_df,
            selected_city=selected_city,
            selected_streets=selected_streets,
            include_all_city_streets=include_all_city_streets,
            max_map_streets=max_map_streets,
            map_data_source=map_data_source,
            reference=reference,
            measures=measures,
            alerts_df=alerts_df,
            anomalies_df=anomalies_df,
            optimized_df=optimized_df,
            kpis=kpis,
            threshold=threshold,
            available_timestamps=available_timestamps,
            forecast_df=forecast_df,
            event_frame=event_frame,
        )
    elif selected_view == "Modelle":
        render_model_tab(metrics_df, predictions, y_test, ts_test, best_model_name)
    else:
        render_data_tab(model_df, city_street_df, selected_city, selected_streets, event_frame)
