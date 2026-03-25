# Traffic Prediction & Optimization

Dieses Repository enthält ein vollständiges Beispielprojekt zur Vorhersage von Verkehrsaufkommen mit Machine Learning. Der Fokus liegt auf Zeitreihenanalyse, Feature Engineering, dem Vergleich mehrerer Modellansätze sowie der Visualisierung und operativen Nutzung der Ergebnisse.

Das Projekt eignet sich als Lernprojekt, Prototyp und als Grundlage für produktive Smart-City- oder Verkehrsmanagement-Anwendungen.

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
- API-orientierte Ausgabe für Integrationen

## Zielarchitektur

Das Projekt ist auf eine erweiterbare Architektur mit TomTom Traffic API, Ticketmaster Events, eigener Datenbank, FastAPI und Streamlit ausgelegt.

Bausteine:

- TomTom Traffic API für aktuelle Flow- und Incident-Daten
- Ticketmaster Discovery API für stadtbezogene Event-Importe
- FastAPI als Backend-Schicht für Ingestion und vereinheitlichte Endpunkte
- Eigene Datenbank für persistierte Traffic-Snapshots
- Streamlit als Leitstellen- und Analyse-Frontend
- Machine-Learning-Pipeline auf Basis eigener historischer Daten

Aktuelle Backend-Endpunkte:

- `GET /health`
- `GET /traffic/flow`
- `GET /traffic/incidents`
- `POST /ingestion/snapshot`
- `POST /events/import/ticketmaster`
- `GET /events`

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

- synthetisch generierte, realistische Verkehrsdaten
- Import eigener CSV-Dateien
- historische CSVs für Kartenansichten
- JSON-basierte Live-APIs für Verkehrsdaten

## Workflow im Notebook

1. Daten laden oder generieren
2. Explorative Datenanalyse
3. Feature Engineering
4. Zeitreihen-konformer Train/Test-Split
5. Modelltraining
6. Evaluation und Vergleich
7. Visualisierung der Prognosen
8. Optionale Modelloptimierung

Typische Analysebausteine:

- Zeitverläufe
- Tages- und Wochenmuster
- Verteilungen
- Kalenderfeatures
- Lag-Features
- Rolling Statistics
- Wetter- und Feiertagsindikatoren

## Streamlit App

Neben den Notebooks enthält das Repository eine modulare Streamlit-Anwendung für Prognose, Kartenansicht und Maßnahmenplanung.

Funktionen der App:

- Modellvergleich auf Basis historischer Verkehrsdaten
- Rekursive Vorhersage für zukünftige Zeiträume
- Maßnahmenbasierte Verkehrsoptimierung
- KPI-Dashboard mit Alerts und Anomalie-Erkennung
- Kartenansicht für Straßenbelastung
- API-Modus für strukturierte JSON-Ausgaben
- Optionale Anbindung an ein FastAPI-Backend als Datenquelle

## Repository-Struktur

```text
.
|-- data/                  Datensätze und Referenzdaten
|-- docs/                  Projektdokumentation
|   |-- ai/                KI-bezogene Offenlegung
|   |-- guides/            Leitfäden
|   `-- reference/         Glossar und Referenzen
|-- notebooks/             Analyse-, Konzept- und EDA-Notebooks
|-- src/                   Streamlit-App, FastAPI und Python-Pakete
|   |-- app.py             Einstiegspunkt für Streamlit
|   |-- api.py             Einstiegspunkt für FastAPI
|   |-- traffic_app/       Modulare Streamlit-Logik
|   `-- traffic_backend/   Modulare Backend-Logik
|-- .env.example
|-- Dockerfile
|-- docker-compose.yml
|-- package.json
|-- requirements.txt
`-- README.md
```

## Anwendung starten

### Lokal

Streamlit starten:

```bash
pip install -r requirements.txt
streamlit run src/app.py
```

FastAPI starten:

```bash
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
docker compose up --build
```

Danach ist die Streamlit-App unter `http://localhost:8501` erreichbar.  
Das Backend läuft unter `http://localhost:8000`.

## Wichtige Inhalte

### Anwendung

- `src/app.py` - schlanker Einstiegspunkt für Streamlit
- `src/traffic_app/` - modulare Fachlogik für Daten, Karten, Forecasting, Optimierung und UI
- `src/api.py` - Einstiegspunkt für FastAPI
- `src/traffic_backend/` - Backend-Logik für Konfiguration, Datenbank, TomTom-Client und API-Endpunkte

### Notebooks

- `notebooks/Q-Phase_Conception.ipynb` - Konzeptphase
- `notebooks/U-Phase_EDA.ipynb` - explorative Datenanalyse
- `notebooks/A-Phase.ipynb` - weiterführende Analyse

### Dokumentation

- `docs/guides/user-guide.md` - Nutzer- und Projektleitfaden
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
- Demonstratoren für Forecasting, Visual Analytics und API-Ausgabe

## Konfiguration

Für das Backend kann eine `.env` auf Basis von `.env.example` verwendet werden.

Wichtige Variablen:

- `TOMTOM_API_KEY`
- `TICKETMASTER_API_KEY`
- `DATABASE_URL`
- `BACKEND_API_TOKEN`
- `DEFAULT_BBOX`

## Entwicklungsnotizen

- Python-Abhängigkeiten liegen zentral in `requirements.txt`
- Die Streamlit-App ist modular unter `src/traffic_app/` aufgebaut
- Das FastAPI-Backend liegt modular unter `src/traffic_backend/`
- Generierte Artefakte wie `node_modules`, `__pycache__` und IDE-Dateien sind über `.gitignore` ausgeschlossen
- Docker und lokaler Start nutzen dieselben Entry Points

