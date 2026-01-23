# 🚦 Traffic Prediction & Optimization

Dieses Repository enthält ein vollständiges Beispielprojekt zur **Vorhersage von Verkehrsaufkommen mithilfe von Machine Learning**.  
Der Fokus liegt auf der Analyse von Zeitreihendaten, Feature Engineering, dem Vergleich verschiedener Modellansätze sowie der Visualisierung von Prognosen.

Das Projekt ist modular aufgebaut und eignet sich sowohl als **Lernprojekt**, **Prototyp** als auch als **Grundlage für produktive Smart-City- oder Verkehrsmanagement-Anwendungen**.


## 📌 Projektübersicht

Ziel des Projekts ist es, Verkehrsaufkommen auf Basis historischer Daten zuverlässig vorherzusagen und unterschiedliche Modellansätze systematisch zu vergleichen.  
Dabei wird der komplette Workflow abgebildet:

- Datenbereitstellung
- Explorative Datenanalyse (EDA)
- Feature Engineering
- Modelltraining
- Evaluation und Modellvergleich
- Visualisierung der Ergebnisse


## 📊 Datengrundlage

### Pflichtspalten
- `ds` – Zeitstempel (Datetime)
- `y` – Verkehrsaufkommen (numerisch)

### Optionale Zusatzdaten
- Wetterinformationen
- Feiertagsindikatoren
- Abgeleitete Variablen (z. B. Geschwindigkeit)

Das Projekt unterstützt:
- **synthetisch generierte, realistische Verkehrsdaten**
- **Import eigener CSV-Dateien**


## 🔄 Workflow im Notebook

1. **Daten laden oder generieren**
2. **Explorative Datenanalyse**
   - Zeitverläufe
   - Tages- und Wochenmuster
   - Verteilungen
3. **Feature Engineering**
   - Kalenderfeatures
   - Lag-Features
   - Rolling Statistics
   - Wetter- und Feiertagsindikatoren
4. **Zeitreihen-konformer Train/Test-Split**
5. **Modelltraining**
6. **Evaluation & Vergleich**
7. **Visualisierung der Prognosen**
8. **Optionale Modelloptimierung**


## 🤖 Implementierte Modelle

- **Lineare Regression**  
  Einfache und interpretierbare Baseline

- **Random Forest Regressor**  
  Leistungsfähiges Ensemble-Modell für nichtlineare Zusammenhänge

- **Prophet (optional)**  
  Spezielles Zeitreihenmodell für Trend- und Saisonalitätsanalyse

- **LSTM (optional)**  
  Deep-Learning-Modell für komplexe zeitliche Abhängigkeiten


## 📈 Evaluationsmetriken

Die Modellleistung wird anhand folgender Metriken bewertet:

- **MAE** – Mean Absolute Error  
- **RMSE** – Root Mean Squared Error  
- **R²** – Bestimmtheitsmaß  

Zusätzlich werden **Ist- und Prognosewerte visuell verglichen**, um qualitative Unterschiede sichtbar zu machen.


## 🧪 Experiment-Tracking (optional)

- Unterstützung für **MLflow**
- Logging von:
  - Modellparametern
  - Metriken
  - Trainierten Modellen


## 🖥️ Voraussetzungen

### Python
- Python ≥ 3.9 empfohlen

### Abhängigkeiten
```bash
pip install numpy pandas matplotlib seaborn scikit-learn
pip install prophet tensorflow mlflow  # optional
