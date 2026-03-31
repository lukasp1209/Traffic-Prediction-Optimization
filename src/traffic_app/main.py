from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .config import CITY_CONFIG_DIR, DEFAULT_DATA, EVENT_CONFIG_DIR
from .data import (
    engineer_features,
    ensure_city_street_schema,
    load_city_street_reference,
    normalize_input,
    read_csv_bytes,
    read_csv_file,
    read_open_traffic_zip_bytes,
)
from .events import (
    apply_event_calendar,
    build_event_frame_for_city,
    load_city_event_reference,
)
from .forecasting import make_recursive_forecast, train_models
from .optimization import (
    build_optimization_plan,
    detect_anomalies,
    detect_congestion_alerts,
    get_selected_measures,
)
from .ui import (
    configure_page,
    render_app_header,
    render_data_tab,
    render_model_tab,
    render_ops_tab,
    render_top_navigation,
)

EMPTY_CITY_DF = pd.DataFrame(columns=["ds", "y", "city", "street"])


def serialize_upload(uploaded: Any) -> dict[str, Any] | None:
    if uploaded is None:
        return None
    return {"name": getattr(uploaded, "name", "upload.csv"), "bytes": uploaded.getvalue()}


def load_primary_data(source: str, uploaded_payload: dict[str, Any] | None) -> pd.DataFrame:
    if source == "Darmstadt Testdatensatz":
        if not DEFAULT_DATA.exists():
            raise FileNotFoundError(f"Datei nicht gefunden: {DEFAULT_DATA}")
        return read_csv_file(str(DEFAULT_DATA))
    if source == "Open Traffic Data ZIP":
        if uploaded_payload is None:
            raise ValueError("Bitte eine ZIP-Datei aus Open Traffic Data hochladen.")
        return read_open_traffic_zip_bytes(uploaded_payload["bytes"], city_name="Darmstadt", intersection_name=uploaded_payload["name"])
    if source == "CSV-Import":
        if uploaded_payload is None:
            raise ValueError("Bitte eine CSV-Datei hochladen.")
        return read_csv_bytes(uploaded_payload["bytes"])
    raise ValueError("Unbekannte Datenquelle.")


def prepare_city_street_data(
    source: str,
    uploaded_payload: dict[str, Any] | None,
    reference,
) -> pd.DataFrame:
    raw_df = load_primary_data(source, uploaded_payload)
    normalized_df = normalize_input(raw_df)
    uses_demo_city_streets = (
        source == "Darmstadt Testdatensatz"
        and "city" not in normalized_df.columns
        and "street" not in normalized_df.columns
    )
    if source != "Darmstadt Testdatensatz" and not {"city", "street"}.issubset(set(normalized_df.columns)):
        raise ValueError("Neue Städte müssen per CSV mit den Spalten city, street, ds und y geliefert werden.")
    if uses_demo_city_streets:
        return ensure_city_street_schema(normalized_df, reference)
    return normalized_df.copy()


def load_map_traffic_data(
    map_data_source: str,
    map_uploaded_payload: dict[str, Any] | None,
    city_street_df: pd.DataFrame,
    reference,
) -> pd.DataFrame:
    if map_data_source == "Historische CSV":
        if map_uploaded_payload is None:
            st.warning("Kartenquelle 'Historische CSV' aktiv, aber keine Datei hochgeladen. Es wird der Datensatz verwendet.")
            return city_street_df.copy()
        try:
            map_raw = read_csv_bytes(map_uploaded_payload["bytes"])
            return ensure_city_street_schema(normalize_input(map_raw), reference)
        except Exception as exc:
            st.warning(f"Historische CSV konnte nicht geladen werden ({exc}). Es wird der Datensatz verwendet.")
            return city_street_df.copy()

    return city_street_df.copy()


def build_selected_city_series(city_street_df: pd.DataFrame, selected_city: str) -> pd.DataFrame:
    selected_city_df = (
        city_street_df[city_street_df["city"] == selected_city]
        .groupby("ds", as_index=False)["y"]
        .sum()
        .sort_values("ds")
        .reset_index(drop=True)
    )
    if selected_city_df.empty:
        raise ValueError("Für die ausgewählte Stadt liegen keine historischen Forecast-Daten vor. Bitte CSV-Daten für diese Stadt laden.")
    return selected_city_df


def get_available_timestamps(
    map_traffic_df: pd.DataFrame,
    selected_city: str,
    include_all_city_streets: bool,
    selected_streets: list[str],
) -> list[pd.Timestamp]:
    street_level_selected_df = map_traffic_df[map_traffic_df["city"] == selected_city].copy()
    if not include_all_city_streets and selected_streets:
        street_level_selected_df = street_level_selected_df[street_level_selected_df["street"].isin(selected_streets)].copy()

    available_timestamps = pd.to_datetime(street_level_selected_df["ds"], errors="coerce").dropna().sort_values().drop_duplicates().tolist()
    if available_timestamps:
        return available_timestamps

    fallback_now = pd.Timestamp.utcnow().tz_localize(None)
    st.warning("Keine gültigen Zeitstempel für die Kartenquelle gefunden. Es wird ein aktueller Zeitpunkt verwendet.")
    return [fallback_now, fallback_now]


def store_analysis_state(**kwargs: Any) -> None:
    st.session_state["analysis_state"] = kwargs


def run_app() -> None:
    configure_page()

    reference = load_city_street_reference(str(CITY_CONFIG_DIR))
    event_reference = load_city_event_reference(str(EVENT_CONFIG_DIR))

    with st.sidebar:
        st.markdown("## Steuerung")
        with st.expander("Daten", expanded=True):
            source = st.radio("Datenquelle", ("Darmstadt Testdatensatz", "Open Traffic Data ZIP", "CSV-Import"))
            split_ratio = st.slider("Train-Anteil", min_value=0.6, max_value=0.9, value=0.8, step=0.05)

            uploaded = None
            if source == "Open Traffic Data ZIP":
                uploaded = st.file_uploader("Open-Traffic-Data ZIP hochladen", type=["zip"])
                st.caption("Die ZIP wird als Darmstadt-Rohdatenimport interpretiert und automatisch auf Stundenwerte verdichtet.")
            elif source == "CSV-Import":
                uploaded = st.file_uploader("CSV-Datei hochladen", type=["csv"])

    uploaded_payload = serialize_upload(uploaded)

    preview_error = None
    try:
        preview_city_street_df = prepare_city_street_data(
            source=source,
            uploaded_payload=uploaded_payload,
            reference=reference,
        )
    except Exception as exc:
        preview_city_street_df = EMPTY_CITY_DF.copy()
        preview_error = str(exc)

    with st.sidebar:
        with st.expander("Raumbezug", expanded=True):
            if preview_error:
                st.caption("Stadtauswahl wird aktiv, sobald eine gültige Datenquelle geladen ist.")
                selected_city = st.text_input("Stadt", value="Darmstadt").strip() or "Darmstadt"
                selected_streets = []
            else:
                dataset_city_options = sorted(preview_city_street_df["city"].dropna().unique().tolist())
                selector_options = dataset_city_options + ["Andere Stadt in Deutschland..."]
                city_choice = st.selectbox("Stadt", selector_options, index=0 if dataset_city_options else len(selector_options) - 1)

                if city_choice == "Andere Stadt in Deutschland...":
                    selected_city = st.text_input("Beliebige Stadt in Deutschland", value="Darmstadt").strip() or "Darmstadt"
                else:
                    selected_city = city_choice

                street_options = sorted(
                    preview_city_street_df.loc[preview_city_street_df["city"] == selected_city, "street"].dropna().unique().tolist()
                )
                if street_options:
                    selected_streets = st.multiselect("Straßenfilter für Karte", options=street_options, default=[])
                    st.caption("Keine Auswahl bedeutet: alle darstellbaren Straßen der Stadt auf der Karte anzeigen.")
                else:
                    selected_streets = []
                    st.caption("Keine lokalen Straßendaten für diese Stadt im Datensatz. Für die Karte werden OSM-Straßen verwendet.")

        with st.expander("Kartenquelle", expanded=False):
            map_data_source = st.selectbox(
                "Auslastungsdaten",
                ("Primärdatensatz", "Historische CSV"),
            )
            fast_map_mode = st.checkbox("Schnellmodus für Karte", value=True)
            include_all_city_streets = st.checkbox("Alle OSM-Straßen der Stadt anzeigen", value=False)
            max_map_streets = st.slider("Max. Straßen auf Karte", min_value=500, max_value=10000, value=3000, step=500)
            if fast_map_mode:
                st.caption("Schnellmodus vermeidet große Overpass-Abfragen und bevorzugt lokale oder bereits gecachte Geometrien.")

            map_uploaded_csv = None

            if map_data_source == "Historische CSV":
                map_uploaded_csv = st.file_uploader("Historische Verkehrs-CSV (city, street, ds, y)", type=["csv"], key="map_hist_csv")

        with st.expander("Optimierung", expanded=False):
            target_reduction = st.slider("Ziel: Reduktion Verkehrsaufkommen (%)", 1, 30, 12)
            measures = get_selected_measures()

        with st.expander("Event-Kalender", expanded=False):
            st.caption("Events werden als zusätzliche Einflussgröße im Datensatz und Forecast berücksichtigt.")
            default_event_frame = build_event_frame_for_city(selected_city, event_reference)
            event_frame = st.data_editor(
                default_event_frame,
                key=f"event_calendar_editor_{selected_city}",
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

        if st.button("Analyse aktualisieren", type="primary", use_container_width=True):
            if preview_error:
                st.error(preview_error)
            else:
                store_analysis_state(
                    source=source,
                    split_ratio=split_ratio,
                    uploaded_payload=uploaded_payload,
                    selected_city=selected_city,
                    selected_streets=selected_streets,
                    map_data_source=map_data_source,
                    fast_map_mode=fast_map_mode,
                    include_all_city_streets=include_all_city_streets,
                    max_map_streets=max_map_streets,
                    map_uploaded_payload=serialize_upload(map_uploaded_csv),
                    target_reduction=target_reduction,
                    measures=measures,
                    event_frame=event_frame.copy(),
                )
                st.success("Analyseparameter aktualisiert.")

    if "analysis_state" not in st.session_state and preview_error is None:
        store_analysis_state(
            source=source,
            split_ratio=split_ratio,
            uploaded_payload=uploaded_payload,
            selected_city=selected_city,
            selected_streets=selected_streets,
            map_data_source=map_data_source,
            fast_map_mode=fast_map_mode,
            include_all_city_streets=include_all_city_streets,
            max_map_streets=max_map_streets,
            map_uploaded_payload=serialize_upload(map_uploaded_csv),
            target_reduction=target_reduction,
            measures=measures,
            event_frame=event_frame.copy(),
        )

    applied = st.session_state.get("analysis_state")
    if applied is None:
        st.info("Bitte zuerst eine gültige Datenquelle wählen und die Analyse aktualisieren.")
        return

    try:
        city_street_df = prepare_city_street_data(
            source=applied["source"],
            uploaded_payload=applied["uploaded_payload"],
            reference=reference,
        )
        if applied["source"] == "Darmstadt Testdatensatz" and {"city", "street"}.isdisjoint(set(read_csv_file(str(DEFAULT_DATA)).columns)):
            st.info(
                "Hinweis: Die aktuelle Datei enthält keine city/street-Spalten. "
                "Die App verwendet deshalb ein Demo-Straßennetz aus JSON-Dateien unter data/city_streets."
            )

        selected_city_df = build_selected_city_series(city_street_df, applied["selected_city"])
        selected_city_df = apply_event_calendar(selected_city_df, applied["selected_city"], applied["event_frame"])
        model_df = engineer_features(selected_city_df)
        if len(model_df) < 200:
            st.error("Zu wenige Datenpunkte nach Feature Engineering. Mindestens 200 erforderlich.")
            st.stop()

        with st.spinner("Trainiere Modelle und berechne Forecast..."):
            metrics_df, predictions, y_test, ts_test, fitted_models, scaler = train_models(model_df, applied["split_ratio"])
            best_model_name = str(metrics_df.iloc[0]["Algorithmus"])
            best_model = fitted_models[best_model_name]

            st.markdown("#### Prognosezeitraum")

            horizon = st.slider("Wie viele Stunden sollen prognostiziert werden?", 6, 168, 48, 6)
            forecast_df = make_recursive_forecast(
                best_model,
                scaler,
                model_df[["ds", "y"]],
                horizon_hours=horizon,
                selected_city=applied["selected_city"],
                event_frame=applied["event_frame"],
            )

        threshold = float(forecast_df["base_forecast"].quantile(0.75))
        alerts_df = detect_congestion_alerts(forecast_df, threshold)
        anomalies_df = forecast_df[detect_anomalies(forecast_df["base_forecast"])].copy()
        optimized_df, kpis = build_optimization_plan(forecast_df, float(applied["target_reduction"]), applied["measures"])
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Analyse fehlgeschlagen: {exc}")
        return

    render_app_header(applied["selected_city"], applied["map_data_source"], best_model_name)
    selected_view = render_top_navigation()

    if selected_view == "Leitstelle":
        with st.spinner("Lade Kartendaten..."):
            map_traffic_df = load_map_traffic_data(
                map_data_source=applied["map_data_source"],
                map_uploaded_payload=applied["map_uploaded_payload"],
                city_street_df=city_street_df,
                reference=reference,
            )
            available_timestamps = get_available_timestamps(
                map_traffic_df=map_traffic_df,
                selected_city=applied["selected_city"],
                include_all_city_streets=applied["include_all_city_streets"],
                selected_streets=applied["selected_streets"],
            )

        render_ops_tab(
            city_street_df=city_street_df,
            map_traffic_df=map_traffic_df,
              selected_city=applied["selected_city"],
              selected_streets=applied["selected_streets"],
              include_all_city_streets=applied["include_all_city_streets"],
              max_map_streets=applied["max_map_streets"],
              fast_map_mode=applied["fast_map_mode"],
              map_data_source=applied["map_data_source"],
            reference=reference,
            measures=applied["measures"],
            alerts_df=alerts_df,
            anomalies_df=anomalies_df,
            optimized_df=optimized_df,
            kpis=kpis,
            threshold=threshold,
            available_timestamps=available_timestamps,
            forecast_df=forecast_df,
            event_frame=applied["event_frame"],
        )
    elif selected_view == "Modelle":
        render_model_tab(metrics_df, predictions, y_test, ts_test, best_model_name)
    else:
        render_data_tab(model_df, city_street_df, applied["selected_city"], applied["selected_streets"], applied["event_frame"])
