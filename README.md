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
