from __future__ import annotations

import json
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pydeck as pdk
import seaborn as sns
import streamlit as st

try:
    import folium
    from streamlit_folium import st_folium
except ModuleNotFoundError:
    folium = None
    st_folium = None

from .mapping import build_street_map_data, compute_map_view_state, select_map_time_window


def configure_page() -> None:
    st.set_page_config(page_title="Stadtverkehr Prognose und Optimierung", layout="wide")
    sns.set_theme(style="whitegrid")
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.4rem; padding-bottom: 2rem;}
        div[data-testid="stSidebar"] {border-right: 1px solid rgba(49, 51, 63, 0.12);}
        .app-shell {
            background: linear-gradient(135deg, #f7f2e8 0%, #fffdf8 55%, #eef3f7 100%);
            border: 1px solid rgba(34, 52, 69, 0.10);
            border-radius: 22px;
            padding: 1.2rem 1.4rem 1rem 1.4rem;
            margin-bottom: 1rem;
        }
        .app-eyebrow {
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #7c674d;
            font-size: 0.78rem;
            font-weight: 700;
        }
        .app-title {
            font-size: 2.1rem;
            line-height: 1.1;
            color: #1f3241;
            font-weight: 800;
            margin: 0.2rem 0 0.35rem 0;
        }
        .app-subtitle {
            color: #51616e;
            font-size: 0.98rem;
            margin-bottom: 0.85rem;
        }
        .context-chip {
            display: inline-block;
            background: rgba(31, 50, 65, 0.06);
            color: #1f3241;
            border-radius: 999px;
            padding: 0.32rem 0.7rem;
            margin: 0 0.45rem 0.45rem 0;
            font-size: 0.86rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(selected_city: str, map_data_source: str, best_model_name: str) -> None:
    st.markdown(
        f"""
        <div class="app-shell">
            <div class="app-eyebrow">Traffic Decision Intelligence</div>
            <div class="app-title">Stadtverkehr Leitstelle</div>
            <div class="app-subtitle">
                Prognose, Kartenanalyse und Massnahmenplanung in einer gefuehrten Oberflaeche.
            </div>
            <span class="context-chip">Stadt: {selected_city}</span>
            <span class="context-chip">Quelle: {map_data_source}</span>
            <span class="context-chip">Bestes Modell: {best_model_name}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_top_navigation() -> str:
    options = ["Leitstelle", "Modelle", "Daten"]
    if hasattr(st, "segmented_control"):
        selected = st.segmented_control("Navigation", options=options, default="Leitstelle", selection_mode="single")
        return selected or "Leitstelle"
    return st.radio("Navigation", options=options, horizontal=True)


def render_kpi_card(title: str, value: str) -> None:
    st.metric(title, value)


def format_forecast_view(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    rename_map = {
        "ds": "Zeitpunkt",
        "base_forecast": "Prognose ohne Massnahmen (Verkehrsmenge)",
        "optimized_forecast": "Prognose mit Massnahmen (Verkehrsmenge)",
        "effective_reduction": "Wirksame Reduktion",
        "event_intensity": "Event-Einfluss",
        "is_event": "Event aktiv",
    }
    display_df = df.copy()
    for source_col, target_col in rename_map.items():
        if source_col in display_df.columns:
            display_df = display_df.rename(columns={source_col: target_col})
    if "Zeitpunkt" in display_df.columns:
        display_df["Zeitpunkt"] = pd.to_datetime(display_df["Zeitpunkt"], errors="coerce").dt.strftime("%d.%m.%Y %H:%M")
    if "Wirksame Reduktion" in display_df.columns:
        display_df["Wirksame Reduktion"] = (
            pd.to_numeric(display_df["Wirksame Reduktion"], errors="coerce") * 100
        ).round(1).astype(str) + " %"
    if "Event aktiv" in display_df.columns:
        display_df["Event aktiv"] = display_df["Event aktiv"].map({1: "Ja", 0: "Nein"}).fillna("Nein")
    if columns is not None:
        selected_columns = [rename_map.get(column, column) for column in columns if rename_map.get(column, column) in display_df.columns]
        return display_df[selected_columns]
    return display_df


def format_model_metrics_view(metrics_df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "Algorithmus": "Modell",
        "MAE": "Durchschnittliche Abweichung",
        "RMSE": "Abweichung bei Ausreissern",
        "R2": "Erklaerungsgrad",
    }
    display_df = metrics_df.rename(columns=rename_map).copy()
    if "Erklaerungsgrad" in display_df.columns:
        display_df["Erklaerungsgrad"] = (display_df["Erklaerungsgrad"] * 100).round(1).astype(str) + " %"
    return display_df


def format_event_view(event_df: pd.DataFrame) -> pd.DataFrame:
    display_df = event_df.copy()
    rename_map = {
        "name": "Event",
        "start": "Beginn",
        "end": "Ende",
        "impact_level": "Einfluss",
        "category": "Kategorie",
    }
    display_df = display_df.rename(columns=rename_map)
    for col in ["Beginn", "Ende"]:
        if col in display_df.columns:
            display_df[col] = pd.to_datetime(display_df[col], errors="coerce").dt.strftime("%d.%m.%Y %H:%M")
    return display_df


def apply_time_axis_format(ax, timestamps: pd.Series) -> None:
    ts = pd.to_datetime(timestamps, errors="coerce").dropna()
    if ts.empty:
        return

    total_span_hours = max((ts.max() - ts.min()).total_seconds() / 3600, 1)
    formatter = mdates.DateFormatter("%d.%m.\n%H:%M") if total_span_hours <= 48 else mdates.DateFormatter("%d.%m.%Y\n%H:%M")

    locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center")


def format_timestamp_value(value) -> str:
    timestamp = pd.to_datetime(value, errors="coerce")
    if pd.isna(timestamp):
        return "-"
    return timestamp.strftime("%d.%m.%Y %H:%M")


def build_folium_street_map(map_df: pd.DataFrame, selected_city: str, map_style: str):
    tile_layers = {
        "Standard": ("OpenStreetMap", {"name": "OpenStreetMap", "show": map_style == "Standard"}),
        "Hell": ("CartoDB positron", {"name": "CartoDB Positron", "show": map_style == "Hell"}),
        "Dunkel": ("CartoDB dark_matter", {"name": "CartoDB Dark", "show": map_style == "Dunkel"}),
        "Satellit": (
            "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            {
                "name": "Esri Satellite",
                "attr": "Tiles © Esri",
                "overlay": False,
                "control": True,
                "show": map_style == "Satellit",
            },
        ),
    }

    coords = np.array([coord for path in map_df["street_geometry"] for coord in path], dtype=float)
    center_lon = float(coords[:, 0].mean())
    center_lat = float(coords[:, 1].mean())
    fmap = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles=None, control_scale=True)

    for tile, kwargs in tile_layers.values():
        folium.TileLayer(tile, **kwargs).add_to(fmap)

    for _, row in map_df.iterrows():
        popup_html = (
            f"<b>{row['street']}</b><br>"
            f"Stadt: {selected_city}<br>"
            f"Traffic-Level: {row['traffic_level']}<br>"
            f"Durchschnitt: {row['avg_traffic']:.1f}<br>"
            f"Peak: {row['peak_traffic']:.1f}<br>"
            f"Messpunkte: {int(row['samples'])}"
        )
        if int(row["samples"]) <= 0:
            popup_html += "<br><i>Keine direkte Messung aus der CSV zugeordnet</i>"

        folium.PolyLine(
            locations=[[point[1], point[0]] for point in row["street_geometry"]],
            color=f"rgb({row['color'][0]},{row['color'][1]},{row['color'][2]})",
            weight=max(float(row["width"]) / 2.5, 2.0),
            opacity=0.85 if int(row["samples"]) > 0 else 0.45,
            tooltip=row["street"],
            popup=folium.Popup(popup_html, max_width=320),
        ).add_to(fmap)

    folium.LayerControl(collapsed=False).add_to(fmap)
    return fmap


def render_ops_tab(
        city_street_df: pd.DataFrame,
        map_traffic_df: pd.DataFrame,
        selected_city: str,
        selected_streets: list[str],
        include_all_city_streets: bool,
        max_map_streets: int,
        map_data_source: str,
        reference,
        measures: dict[str, int],
        alerts_df: pd.DataFrame,
        anomalies_df: pd.DataFrame,
        optimized_df: pd.DataFrame,
        kpis: dict[str, float],
        threshold: float,
        available_timestamps: list[pd.Timestamp],
        forecast_df: pd.DataFrame,
        event_frame: pd.DataFrame,
) -> None:
    st.subheader("Operatives Dashboard")

    show_all_streets = include_all_city_streets or not selected_streets
    street_count_label = "alle verfuegbaren/OSM-Strassen" if show_all_streets else str(len(selected_streets))
    context_col, action_col = st.columns([1.1, 0.9])
    with context_col:
        st.markdown("#### Lagebild")
        st.write(
            f"Stadt: **{selected_city}**  \n"
            f"Strassen: **{street_count_label}**  \n"
            f"Datenquelle: **{map_data_source}**"
        )
    with action_col:
        st.markdown("#### Massnahmenmix")
        st.write(
            f"Ampel: **{measures['signal']}**  \n"
            f"OePNV: **{measures['public_transport']}**  \n"
            f"Homeoffice: **{measures['home_office']}**  \n"
            f"Baustellen: **{measures['construction']}**"
        )
        active_events = event_frame.copy()
        if not active_events.empty:
            active_events["start"] = pd.to_datetime(active_events["start"], errors="coerce")
            active_events = active_events[active_events["start"] >= pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=1)]
            active_events = active_events.sort_values("start").head(3)
            if not active_events.empty:
                st.caption("Naechste Events")
                for _, row in active_events.iterrows():
                    st.write(f"- {row['name']} ({pd.Timestamp(row['start']):%d.%m.%Y %H:%M})")

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        render_kpi_card("Ausgangsprognose (Menge)", f"{kpis['baseline_total']:.0f}")
    with kpi2:
        render_kpi_card("Mit Massnahmen (Menge)", f"{kpis['optimized_total']:.0f}")
    with kpi3:
        render_kpi_card("Reduktion", f"{kpis['reduction_pct']:.1f}%")
    with kpi4:
        render_kpi_card("Zielstatus", "erreicht" if kpis["achieved"] else f"-{kpis['gap']:.1f}%")

    left_col, right_col = st.columns([0.95, 1.35])
    with left_col:
        st.markdown("#### Statuscenter")
        alert_col, anomaly_col = st.columns(2)
        with alert_col:
            st.markdown("##### Alerts")
            if alerts_df.empty:
                st.success("Keine kritischen Stunden im aktuellen Forecast.")
            else:
                st.dataframe(
                    format_forecast_view(alerts_df, columns=["ds", "base_forecast"]),
                    use_container_width=True,
                    hide_index=True,
                )
        with anomaly_col:
            st.markdown("##### Anomalien")
            if anomalies_df.empty:
                st.success("Keine Anomalien im aktuellen Forecast.")
            else:
                st.dataframe(
                    format_forecast_view(anomalies_df, columns=["ds", "base_forecast"]),
                    use_container_width=True,
                    hide_index=True,
                )

    with right_col:
        st.markdown("#### Prognosewirkung")
        fig, ax = plt.subplots(figsize=(14, 5))
        ax.plot(optimized_df["ds"], optimized_df["base_forecast"], label="Prognose ohne Massnahmen", linewidth=2)
        ax.plot(
            optimized_df["ds"],
            optimized_df["optimized_forecast"],
            label="Prognose mit Massnahmen",
            linewidth=2,
            linestyle="--",
        )
        ax.axhline(threshold, color="red", linestyle=":", label="kritische Schwelle")
        ax.set_title("Naechste Stunden: Prognose vs. Optimierung")
        ax.set_xlabel("Zeit")
        ax.set_ylabel("Verkehrsmenge je Zeitfenster")
        apply_time_axis_format(ax, optimized_df["ds"])
        ax.legend()
        fig.tight_layout()
        st.pyplot(fig)

    baseline_peaks = int((optimized_df["base_forecast"] >= threshold).sum())
    optimized_peaks = int((optimized_df["optimized_forecast"] >= threshold).sum())
    st.caption(f"Staukritische Stunden (Schwelle {threshold:.0f}): vorher {baseline_peaks}, nachher {optimized_peaks}.")
    st.caption("Hinweis: Prognosewerte sind absolute Verkehrsmengen je Zeitfenster, keine Prozentwerte.")

    st.markdown("#### Kartenansicht")
    map_start_ts, map_end_ts = select_map_time_window(available_timestamps)
    st.caption(f"Ausgewaehlter Zeitraum: {map_start_ts:%d.%m.%Y %H:%M} bis {map_end_ts:%d.%m.%Y %H:%M}")
    style_options = ["Standard", "Hell", "Dunkel", "Satellit"] if folium is not None else ["Hell", "Dunkel"]
    map_style = st.selectbox("Kartenstil", style_options, index=0)

    map_df = build_street_map_data(
        city_street_df=city_street_df,
        selected_city=selected_city,
        selected_streets=selected_streets,
        start_ts=pd.Timestamp(map_start_ts),
        end_ts=pd.Timestamp(map_end_ts),
        reference=reference,
        include_all_city_streets=include_all_city_streets,
        max_streets=max_map_streets,
        traffic_df=map_traffic_df,
    )

    if not show_all_streets:
        mapped_streets = set(map_df["street"].tolist()) if not map_df.empty else set()
        unmapped_streets = [street for street in selected_streets if street not in mapped_streets]
        if unmapped_streets:
            st.warning(
                "Fuer folgende Strassen konnte keine passende OSM-Geometrie geladen werden: "
                + ", ".join(unmapped_streets)
            )
    elif map_df.empty:
        st.warning("Overpass konnte keine Strassengeometrien fuer die Stadt laden.")

    if map_df.empty:
        st.info("Keine Kartendaten im gewaehlten Zeitraum oder keine passenden OSM-Strassengeometrien.")
    else:
        if folium is not None and st_folium is not None:
            folium_map = build_folium_street_map(map_df, selected_city, map_style)
            st_folium(folium_map, use_container_width=True, height=720, returned_objects=[])
            st.caption(
                "Farben: Gruen = niedrig, Gelb = mittel, Rot = hoch, Grau = keine Traffic-Messung | "
                "Strassen sind klickbar und zeigen Details im Popup | "
                f"Quelle: {map_data_source} | "
                f"Zeitraum {pd.Timestamp(map_start_ts):%d.%m.%Y %H:%M} bis {pd.Timestamp(map_end_ts):%d.%m.%Y %H:%M}"
            )
        else:
            st.info("Fuer klickbare Karte und Satellitenansicht bitte einmal `pip install -r requirements.txt` ausfuehren.")
            line_layer = pdk.Layer(
                "PathLayer",
                data=map_df,
                get_path="street_geometry",
                get_color="color",
                get_width="width",
                width_min_pixels=4,
                pickable=True,
                auto_highlight=True,
                rounded=True,
                cap_rounded=True,
                joint_rounded=True,
                opacity=0.78,
            )
            deck = pdk.Deck(
                layers=[line_layer],
                initial_view_state=compute_map_view_state(map_df, selected_city),
                map_provider="carto",
                map_style="light_no_labels" if map_style == "Hell" else "dark_no_labels",
                tooltip={
                    "html": (
                        "<b>{street}</b><br/>"
                        "Auslastung: {traffic_level}<br/>"
                        "Durchschnittliches Aufkommen: {avg_traffic}<br/>"
                        "Spitzenwert: {peak_traffic}<br/>"
                        "Messpunkte: {samples}"
                    )
                },
            )
            st.pydeck_chart(deck, use_container_width=True, height=720)

    recommendation = "Massnahmenplan ist ausreichend fuer den Zielwert."
    if not kpis["achieved"]:
        recommendation = (
            "Ziel noch nicht erreicht: Erhoehen Sie zuerst Ampelsteuerung und OePNV, "
            "danach Homeoffice-Kampagnen fuer Spitzenzeiten."
        )
    st.info(recommendation)

    st.download_button(
        "Optimierungsplan als JSON herunterladen",
        data=json.dumps(
            {
                "city": selected_city,
                "streets": selected_streets,
                "threshold": threshold,
                "measures": measures,
                "kpis": kpis,
                "forecast": forecast_df.tail(24).to_dict(orient="records"),
                "optimized_forecast": optimized_df.tail(24)[["ds", "base_forecast", "optimized_forecast", "effective_reduction"]].to_dict(orient="records"),
                "alerts": alerts_df.to_dict(orient="records"),
                "anomalies": anomalies_df.to_dict(orient="records"),
            },
            default=str,
        ).encode("utf-8"),
        file_name="traffic_optimization_plan.json",
        mime="application/json",
    )


def render_model_tab(metrics_df: pd.DataFrame, predictions: dict[str, np.ndarray], y_test: pd.Series, ts_test: pd.Series, best_model_name: str) -> None:
    st.subheader("Modellvergleich")
    st.caption(
        "Die Tabelle zeigt, wie gut die Modelle das Verkehrsaufkommen treffen. "
        "Kleinere Abweichungen sind besser, ein hoeherer Erklaerungsgrad ist besser."
    )
    st.dataframe(format_model_metrics_view(metrics_df), use_container_width=True, hide_index=True)
    st.success(f"Bestes Modell bei starken Abweichungen: {best_model_name}")

    selected_model = st.selectbox("Verlauf fuer Modell", list(predictions.keys()), index=0)
    n_show = min(7 * 24, len(y_test))
    ts_show = ts_test.iloc[-n_show:]
    y_show = y_test.iloc[-n_show:]
    y_pred_show = predictions[selected_model][-n_show:]

    fig, ax = plt.subplots(figsize=(14, 4))
    ax.plot(ts_show, y_show.values, label="Ist", color="black", linewidth=2)
    ax.plot(ts_show, y_pred_show, label="Prognose", linestyle="--", linewidth=2)
    ax.set_title(f"Ist vs. Prognose: {selected_model}")
    ax.set_xlabel("Zeit")
    ax.set_ylabel("Verkehrsmenge je Zeitfenster")
    apply_time_axis_format(ax, ts_show)
    ax.legend()
    fig.tight_layout()
    st.pyplot(fig)


def render_data_tab(
        model_df: pd.DataFrame,
        city_street_df: pd.DataFrame,
        selected_city: str,
        selected_streets: list[str],
        event_frame: pd.DataFrame,
) -> None:
    st.subheader("Datengrundlage")
    c1, c2, c3 = st.columns(3)
    c1.metric("Messpunkte", f"{len(model_df):,}".replace(",", "."))
    c2.metric("Zeitraum ab", format_timestamp_value(model_df["ds"].min()))
    c3.metric("Zeitraum bis", format_timestamp_value(model_df["ds"].max()))

    st.markdown(f"**Stadt:** {selected_city}")
    st.markdown(
        f"**Strassen in Auswahl:** {', '.join(selected_streets) if selected_streets else 'Alle darstellbaren Strassen der Stadt'}"
    )
    st.dataframe(format_forecast_view(model_df.tail(48)), use_container_width=True, hide_index=True)

    if not event_frame.empty:
        st.markdown("#### Event-Kalender")
        st.dataframe(format_event_view(event_frame.sort_values("start")), use_container_width=True, hide_index=True)

    street_overview_source = city_street_df[city_street_df["city"] == selected_city]
    if selected_streets:
        street_overview_source = street_overview_source[street_overview_source["street"].isin(selected_streets)]

    street_overview = (
        street_overview_source.groupby("street", as_index=False)["y"]
        .mean()
        .sort_values("y", ascending=False)
        .rename(columns={"y": "Durchschnittliches Verkehrsaufkommen"})
    )
    st.dataframe(street_overview, use_container_width=True, hide_index=True)

    fig, ax = plt.subplots(figsize=(10, 4))
    hourly = model_df.groupby("hour")["y"].mean()
    ax.plot(hourly.index, hourly.values, marker="o")
    ax.set_xticks(range(24))
    ax.set_title("Durchschnittlicher Verkehr je Stunde")
    ax.set_xlabel("Stunde")
    ax.set_ylabel("Durchschnittliche Verkehrsmenge je Zeitfenster")
    st.pyplot(fig)
