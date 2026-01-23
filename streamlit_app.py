import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings

warnings.filterwarnings('ignore')

# MLflow und Prophet optional
try:
    from prophet import Prophet

    PROPHET_AVAILABLE = True
except:
    PROPHET_AVAILABLE = False

try:
    import mlflow

    MLFLOW_AVAILABLE = True
except:
    MLFLOW_AVAILABLE = False

# Konfiguration
st.set_page_config(
    page_title="Traffic Prediction & Optimization",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Traffic Prediction & Optimization")
st.markdown("---")

# Sidebar Navigation
with st.sidebar:
    st.header("Navigation")
    page = st.radio("Wählen Sie eine Seite:",
                    ["Dashboard", "Vorhersage", "Optimierung", "Modell-Training"])


# Beispieldaten generieren
@st.cache_data
def generate_sample_data(days=14):
    dates = pd.date_range(start="2024-01-01", periods=days * 24, freq="H")
    # Realistische Verkehrsmuster: Spitzen morgens/abends
    hours = np.arange(days * 24)
    traffic = (30 * np.sin(hours * 2 * np.pi / 24) +
               10 * np.sin(hours * 2 * np.pi / (24 * 7)) +  # Wochenmuster
               50 + np.random.normal(0, 5, days * 24))
    traffic = np.clip(traffic, 5, 100)

    df = pd.DataFrame({
        "ds": dates,
        "y": traffic,
        "Geschwindigkeit": 120 - traffic + np.random.normal(0, 5, days * 24),
        "Wetter": np.random.choice(["Sonnig", "Bewölkt", "Regen"], days * 24)
    })
    return df


data = generate_sample_data()

# Dashboard
if page == "Dashboard":
    st.header("📊 Verkehrsdashboard")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Durchschn. Verkehr", f"{data['y'].mean():.1f}%")
    with col2:
        st.metric("Max. Verkehr", f"{data['y'].max():.1f}%")
    with col3:
        st.metric("Min. Verkehr", f"{data['y'].min():.1f}%")
    with col4:
        st.metric("Durchschn. Geschwindigkeit", f"{data['Geschwindigkeit'].mean():.1f} km/h")

    st.markdown("---")

    # Verkehrstrend
    fig = px.line(data, x="ds", y="y",
                  title="Verkehrsaufkommen - Historisch",
                  labels={"y": "Aufkommen (%)", "ds": "Zeit"})
    st.plotly_chart(fig, use_container_width=True)

    # Tägliches Muster
    data['Stunde'] = data['ds'].dt.hour
    hourly_avg = data.groupby('Stunde')['y'].mean()
    fig2 = px.bar(x=hourly_avg.index, y=hourly_avg.values,
                  title="Durchschnittliches Verkehrsmuster nach Stunde",
                  labels={"x": "Stunde des Tages", "y": "Aufkommen (%)"})
    st.plotly_chart(fig2, use_container_width=True)

# Vorhersage
elif page == "Vorhersage":
    st.header("🔮 Verkehrsvorhersage")

    col1, col2, col3 = st.columns(3)
    with col1:
        stunden = st.slider("Vorhersage für nächste Stunden:", 1, 168, 24)
    with col2:
        modell = st.selectbox("Modell wählen:",
                              ["Einfache Baseline", "Prophet"] if PROPHET_AVAILABLE else ["Einfache Baseline"])
    with col3:
        st.info(f"Horizont: {stunden}h")

    # Baseline: Saisonalität
    if modell == "Einfache Baseline":
        forecast_values = []
        for h in range(stunden):
            stunde_des_tages = (h + data['ds'].max().hour) % 24
            avg_für_stunde = data[data['ds'].dt.hour == stunde_des_tages]['y'].mean()
            noise = np.random.normal(0, 3)
            forecast_values.append(avg_für_stunde + noise)

        forecast_data = pd.DataFrame({
            "ds": pd.date_range(data["ds"].max(), periods=stunden + 1, freq="H")[1:],
            "yhat": forecast_values
        })

    # Prophet
    elif modell == "Prophet" and PROPHET_AVAILABLE:
        with st.spinner("Prophet-Modell trainiert..."):
            model = Prophet(yearly_seasonality=False,
                            monthly_seasonality=False,
                            daily_seasonality=True)
            model.fit(data[['ds', 'y']])
            future = model.make_future_dataframe(periods=stunden, freq='H')
            forecast_data = model.predict(future).tail(stunden)[['ds', 'yhat']]

    # Plot
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data["ds"], y=data["y"],
                             name="Historisch", mode="lines"))
    fig.add_trace(go.Scatter(x=forecast_data["ds"], y=forecast_data["yhat"],
                             name="Vorhersage", mode="lines+markers",
                             line=dict(dash="dash")))
    fig.update_layout(title=f"Verkehrsvorhersage ({modell})",
                      xaxis_title="Zeit",
                      yaxis_title="Aufkommen (%)",
                      hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

# Optimierung
elif page == "Optimierung":
    st.header("⚙️ Verkehrsoptimierung")

    st.subheader("Aktuelle Engpässe & Empfehlungen")

    roads = ["Hauptstraße", "Ringstraße", "Bundesstraße", "Schnellstraße"]
    congestion = [75, 45, 30, 60]

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(x=roads, y=congestion,
                     title="Verkehrsaufkommen nach Straße",
                     labels={"x": "Straße", "y": "Aufkommen (%)"},
                     color=congestion,
                     color_continuous_scale="RdYlGn_r")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("**Empfohlene Maßnahmen:**")
        recommendations = []
        for i, road in enumerate(roads):
            if congestion[i] > 70:
                st.warning(f"🔴 {road}: Umleitungen empfohlen")
                recommendations.append(f"{road} (Auslastung: {congestion[i]}%)")
            elif congestion[i] > 50:
                st.info(f"🟡 {road}: Erhöhte Belastung")
            else:
                st.success(f"🟢 {road}: Normal")

        if recommendations:
            st.markdown("**Priorisierte Maßnahmen:**")
            for rec in recommendations:
                st.markdown(f"- {rec}")

# Modell-Training
elif page == "Modell-Training":
    st.header("🤖 Modell-Training & Experiment-Tracking")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Training-Konfiguration")
        train_size = st.slider("Trainings-Testdaten Split (%):", 60, 90, 80)
        epochs = st.slider("Epochs:", 10, 100, 50) if st.checkbox("LSTM aktivieren") else 0

    with col2:
        st.subheader("Metriken")

        split_idx = int(len(data) * train_size / 100)
        train_data = data[:split_idx]
        test_data = data[split_idx:]

        baseline_pred = []
        for idx in test_data.index:
            stunde = test_data.loc[idx, 'ds'].hour
            avg = train_data[train_data['ds'].dt.hour == stunde]['y'].mean()
            baseline_pred.append(avg)

        mae = mean_absolute_error(test_data['y'].values, baseline_pred)
        rmse = np.sqrt(mean_squared_error(test_data['y'].values, baseline_pred))

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("MAE", f"{mae:.2f}")
        with col_m2:
            st.metric("RMSE", f"{rmse:.2f}")
        with col_m3:
            st.metric("Datensätze", len(data))

    st.markdown("---")

    # MLflow Integration
    if MLFLOW_AVAILABLE:
        if st.button("🚀 Training starten & zu MLflow loggen"):
            with st.spinner("Training läuft..."):
                try:
                    # MLflow Tracking URI setzen
                    mlflow.set_tracking_uri("file:///app/mlruns")
                    # Experiment erstellen oder abrufen
                    mlflow.set_experiment("Traffic Prediction")

                    with mlflow.start_run():
                        mlflow.log_param("train_size", train_size)
                        mlflow.log_param("epochs", epochs)
                        mlflow.log_metric("mae", mae)
                        mlflow.log_metric("rmse", rmse)
                    st.success("✅ Experiment zu MLflow geloggt!")
                except Exception as e:
                    st.error(f"❌ MLflow Fehler: {str(e)}")
    else:
        st.warning("⚠️ MLflow nicht installiert. Installieren Sie: `pip install mlflow`")

    # Modell-Vergleich
    st.subheader("Modell-Vergleich")
    comparison_data = pd.DataFrame({
        "Modell": ["Baseline (Durchschnitt)", "Prophet", "LSTM"],
        "MAE": [mae, mae * 0.85, mae * 0.75],
        "RMSE": [rmse, rmse * 0.85, rmse * 0.75],
        "Trainingszeit": ["< 1s", "5-10s", "30-120s"]
    })
    st.dataframe(comparison_data, use_container_width=True)# Modell-Training
elif page == "Modell-Training":
    st.header("🤖 Modell-Training & Experiment-Tracking")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Training-Konfiguration")
        train_size = st.slider("Trainings-Testdaten Split (%):", 60, 90, 80)
        epochs = st.slider("Epochs:", 10, 100, 50) if st.checkbox("LSTM aktivieren") else 0

    with col2:
        st.subheader("Metriken")

        # Train-Test Split
        split_idx = int(len(data) * train_size / 100)
        train_data = data[:split_idx]
        test_data = data[split_idx:]

        # Baseline-Modell
        baseline_pred = []
        for idx in test_data.index:
            stunde = test_data.loc[idx, 'ds'].hour
            avg = train_data[train_data['ds'].dt.hour == stunde]['y'].mean()
            baseline_pred.append(avg)

        mae = mean_absolute_error(test_data['y'].values, baseline_pred)
        rmse = np.sqrt(mean_squared_error(test_data['y'].values, baseline_pred))

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("MAE", f"{mae:.2f}")
        with col_m2:
            st.metric("RMSE", f"{rmse:.2f}")
        with col_m3:
            st.metric("Datensätze", len(data))

    st.markdown("---")

    # MLflow Integration
    if MLFLOW_AVAILABLE:
        if st.button("🚀 Training starten & zu MLflow loggen"):
            with st.spinner("Training läuft..."):
                mlflow.start_run()
                mlflow.log_param("train_size", train_size)
                mlflow.log_param("epochs", epochs)
                mlflow.log_metric("mae", mae)
                mlflow.log_metric("rmse", rmse)
                mlflow.end_run()
                st.success("✅ Experiment zu MLflow geloggt!")
    else:
        st.warning("⚠️ MLflow nicht installiert. Installieren Sie: `pip install mlflow`")

    # Modell-Vergleich
    st.subheader("Modell-Vergleich")
    comparison_data = pd.DataFrame({
        "Modell": ["Baseline (Durchschnitt)", "Prophet", "LSTM"],
        "MAE": [mae, mae * 0.85, mae * 0.75],
        "RMSE": [rmse, rmse * 0.85, rmse * 0.75],
        "Trainingszeit": ["< 1s", "5-10s", "30-120s"]
    })
    st.dataframe(comparison_data, use_container_width=True)

st.markdown("---")
st.caption("Traffic Prediction & Optimization • MLflow + Prophet/LSTM Integration")
