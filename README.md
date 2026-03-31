# Traffic Prediction & Optimization

Dieses Repository enthält ein Streamlit-basiertes Projekt zur Vorhersage von Verkehrsaufkommen mit Machine Learning. Der Fokus liegt auf Zeitreihenanalyse, Feature Engineering, Modellvergleich sowie einer lokalen, reproduzierbaren Demo für Prognose, Kartenansicht und Maßnahmenplanung.

## Projektübersicht

Ziel des Projekts ist es, Verkehrsaufkommen auf Basis historischer Daten zuverlässig vorherzusagen und unterschiedliche Modellansätze systematisch zu vergleichen.

Abgedeckter Workflow:

- Datenbereitstellung
- Explorative Datenanalyse (EDA)
- Feature Engineering
- Modelltraining
- Evaluation und Modellvergleich
- Visualisierung der Ergebnisse
- Operative Optimierung über eine Streamlit-Leitstellenansicht

## Zielarchitektur

Das Projekt ist auf eine modulare, lokal lauffähige Streamlit-Architektur mit reproduzierbaren Datenquellen ausgelegt.

Bausteine:

- Lokale historische Verkehrsdaten und Demo-Straßendaten
- JSON-basierte Referenzdaten für Straßen und Events
- Streamlit als Leitstellen- und Analyse-Frontend
- Machine-Learning-Pipeline auf Basis eigener historischer Daten

## Datengrundlage

### Pflichtspalten

- `ds` - Zeitstempel (Datetime)
- `y` - Verkehrsaufkommen (numerisch)

### Optionale Zusatzdaten

- Wetterinformationen
- Feiertagsindikatoren
- Abgeleitete Variablen, zum Beispiel Geschwindigkeit
- Stadt- und Straßenzuordnung über `city` und `street`

Das Projekt unterstützt:

- lokale Demo-Datensätze mit echten Straßennamen
- Import eigener CSV-Dateien
- historische CSVs für Kartenansichten
- JSON-basierte Referenzdaten für lokale Karten- und Event-Demos

## Streamlit App

Neben den Notebooks enthält das Repository eine modulare Streamlit-Anwendung für Prognose, Kartenansicht und Maßnahmenplanung.

Funktionen der App:

- Modellvergleich auf Basis historischer Verkehrsdaten
- Rekursive Vorhersage für zukünftige Zeiträume
- Maßnahmenbasierte Verkehrsoptimierung
- KPI-Dashboard mit Alerts und Anomalie-Erkennung
- Kartenansicht für Straßenbelastung
- Vollständig lokal nutzbar ohne Backend und ohne externe API-Keys

## Repository-Struktur

```text
.
|-- data/                  Datensätze und Referenzdaten
|-- docs/                  Projektdokumentation
|   |-- ai/                KI-bezogene Offenlegung
|   |-- guides/            Leitfäden
|   `-- reference/         Glossar und Referenzen
|-- notebooks/             Analyse-, Konzept- und EDA-Notebooks
|-- src/                   Streamlit-App und Python-Pakete
|   |-- app.py             Einstiegspunkt für Streamlit
|   `-- traffic_app/       Modulare Streamlit-Logik
|-- .env.example
|-- Dockerfile
|-- docker-compose.yml
|-- package.json
|-- requirements.txt
`-- README.md
```

## Anwendung starten

### Lokal

1. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

2. Streamlit starten:

```bash
streamlit run src/app.py
```

### Docker

```bash
docker compose up --build
```

Danach ist die Streamlit-App unter `http://localhost:8501` erreichbar.

## Wichtige Inhalte

### Anwendung

- `src/app.py` - schlanker Einstiegspunkt für Streamlit
- `src/traffic_app/` - modulare Fachlogik für Daten, Karten, Forecasting, Optimierung und UI

### Notebooks

- `notebooks/Q-Phase_Question.ipynb` - Fragestellung und Projektkontext
- `notebooks/U-Phase_Understanding.ipynb` - explorative Datenanalyse und Datenverständnis
- `notebooks/A-Phase_Algorithms.ipynb` - Modelltraining und Vergleich
- `notebooks/C-Phase_Conclude.ipynb` - Bewertung und Entscheidung
- `notebooks/K-Phase_Knowledge.ipynb` - Übergabe und Deployment-Überlegungen

### Dokumentation

- `docs/guides/user-guide.md` - Nutzer- und Projektleitfaden
- `docs/guides/model-card.md` - Model Card
- `docs/reference/glossary.md` - Glossar
- `docs/ai/tool-disclosure.md` - KI-Offenlegung

## Modellierung

Aktuell werden mehrere Regressionsmodelle verglichen, darunter:

- Lineare Regression
- Ridge-Regression
- Random Forest
- Gradient Boosting

Die Bewertung erfolgt über klassische Metriken wie:

- `MAE`
- `RMSE`
- `R2`

## Einsatzszenarien

Das Projekt eignet sich unter anderem für:

- Lern- und Hochschulprojekte im Bereich Data Science
- Prototypen für Smart-City-Anwendungen
- Verkehrsleitstellen und kommunale Entscheidungsunterstützung
- Demonstratoren für Forecasting und Visual Analytics

## Konfiguration

Die Streamlit-App benötigt aktuell keine zwingenden `.env`-Variablen. Die Datei kann leer bleiben oder komplett entfallen.

## Entwicklungsnotizen

- Python-Abhängigkeiten liegen zentral in `requirements.txt`
- Die Streamlit-App ist modular unter `src/traffic_app/` aufgebaut
- Generierte Artefakte wie `node_modules`, `__pycache__` und IDE-Dateien sind über `.gitignore` ausgeschlossen
- Docker und lokaler Start nutzen denselben Streamlit-Entry-Point
