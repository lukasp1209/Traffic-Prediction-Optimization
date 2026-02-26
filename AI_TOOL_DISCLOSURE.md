# Erklärung zur Nutzung von KI-Werkzeugen im Machine-Learning-Projekt  
## 🚦 Projekt: Traffic Prediction & Optimization

Dieses Dokument beschreibt den Einsatz von KI-basierten Werkzeugen im Rahmen des Projekts **Traffic Prediction**.  
Die Gliederung folgt dem **QUA³CK-Prozessmodell**, um transparent darzustellen, in welcher Projektphase welche KI-Werkzeuge zu welchem Zweck eingesetzt wurden.

Das **QUA³CK-Modell** ist ein strukturierter, iterativer Entwicklungsprozess für Machine-Learning-Projekte und steht für:

- **Q** – Question  
- **U** – Understanding  
- **A** – Algorithm Selection  
- **A** – Data Adaption  
- **A** – Parameter Adjustment  
- **C** – Conclusion & Comparison  
- **K** – Knowledge Transfer  

Alle durch KI-Systeme generierten Inhalte (z. B. Code, Visualisierungen, Textvorschläge oder Analysen) wurden von mir als verantwortlichem Entwickler kritisch geprüft, getestet und angepasst.  
Die finale Verantwortung für Architektur, Implementierung und Bewertung liegt vollständig bei mir.

---

# Detaillierte Aufschlüsselung der Werkzeugnutzung nach Phase

| Phase (QUA³CK) | KI-Tool (Version) | Zweck | Beispielhafter Prompt / Anwendungsfall |
|---------------|------------------|--------|----------------------------------------|
| **Q** – Question | GitHub Copilot, ChatGPT (GPT-4/5), Google Gemini | Präzisierung der Prognosefrage, Definition der Zielvariable (Traffic Volume), Strukturierung der Projektarchitektur | „Wie formuliere ich eine klare ML-Fragestellung für eine stündliche Verkehrsprognose?“ |
| **U** – Understanding | ChatGPT, GitHub Copilot | Unterstützung bei Exploratory Data Analysis (EDA), Visualisierungen (Zeitreihe, Heatmap Stunde × Wochentag), Interpretation statistischer Muster | „Erstelle eine Heatmap für Stunde × Wochentag und interpretiere typische Verkehrsprofile.“ |
| **A** – Algorithm Selection | GitHub Copilot, ChatGPT | Vergleich geeigneter Modelle für Zeitreihenprognose (Linear Regression, Random Forest, Gradient Boosting, SARIMA, Prophet) | „Welche Modelle eignen sich für stündliche Verkehrsprognosen mit multipler Saisonalität?“ |
| **A** – Data Adaption | GitHub Copilot | Feature Engineering (Lag-Features, Rolling Means, Kalenderfeatures), Zeitreihen-Splitting | „Erzeuge Lag-Features (1h, 24h, 168h) und Rolling Means in Pandas.“ |
| **A** – Parameter Adjustment | GitHub Copilot | Hyperparameter-Tuning (GridSearchCV, TimeSeriesSplit), Vermeidung von Data Leakage | „Implementiere TimeSeriesSplit für Random Forest ohne Data Leakage.“ |
| **C** – Conclusion & Comparison | ChatGPT, GitHub Copilot | Vergleich von Modellmetriken (RMSE, MAE, R²), Residuenanalyse, Visualisierung von Forecast vs. Ground Truth | „Vergleiche die Modelle anhand RMSE und visualisiere Prognose vs. Ist-Werte.“ |
| **K** – Knowledge Transfer | ChatGPT | Erstellung von Dokumentation (README, Glossar, Methodendokumentation), Interpretation der Ergebnisse für Nicht-Experten | „Erkläre RMSE und Saisonalität für ein nicht-technisches Publikum.“ |

---

# Rolle der KI im Projekt

Die KI-Werkzeuge wurden verwendet als:

- 💡 Ideengeber für Modellansätze  
- 🧠 Sparringspartner für methodische Fragen  
- 🛠 Unterstützung bei Code-Strukturierung  
- 📊 Hilfe bei Visualisierung und Interpretation  
- 📖 Unterstützung bei verständlicher Dokumentation  

Nicht verwendet wurden KI-Systeme zur:

- unkontrollierten Generierung fertiger Projektlösungen  
- automatischen Modellselektion ohne Validierung  
- Übernahme ungeprüfter Ergebnisse  

Alle Vorschläge wurden getestet, angepasst und in den Projektkontext integriert.

---

# Verwendete Datensätze

Im Rahmen des Traffic-Prediction-Projekts wurden folgende Datensätze verwendet:

| Datensatz | Quelle | Beschreibung | Verwendungszweck |
|------------|--------|--------------|------------------|
| **Metro Interstate Traffic Volume Dataset** | UCI Machine Learning Repository | Stündliches Verkehrsaufkommen auf einer US-Interstate-Autobahn inkl. Wetter- und Kalenderdaten | Zentrale Zielvariable (Traffic Volume) für das Training der Prognosemodelle |
| **Wetterdaten (integriert im Datensatz)** | National Weather Service (via UCI) | Temperatur, Regen, Schnee, Bewölkung | Externe Einflussfaktoren als Features |
| **Zeitstempelbasierte Kalenderdaten** | Abgeleitet aus Timestamp | Stunde, Wochentag, Monat, Feiertage | Feature Engineering für Saisonalitätsmodellierung |

*(Falls ein anderer Datensatz verwendet wurde, bitte hier entsprechend anpassen.)*

---

# Methodische Absicherung

Zur Sicherstellung wissenschaftlicher Qualität wurden folgende Maßnahmen umgesetzt:

- Zeitlich korrektes Train-Test-Splitting  
- Verwendung von **TimeSeriesSplit** statt zufälliger Cross-Validation  
- Vermeidung von Data Leakage  
- Vergleich mehrerer Modellklassen  
- Evaluation anhand mehrerer Metriken (RMSE, MAE, R²)  
- Residuenanalyse  

---

# Transparenz & Verantwortung

- KI diente als unterstützendes Werkzeug, nicht als Entscheidungsinstanz.  
- Alle Ergebnisse wurden reproduzierbar implementiert.  
- Modellentscheidungen basieren auf quantitativer Evaluation.  
- Die Verantwortung für das Projekt liegt vollständig beim Entwickler.  

---

# Fazit

Der Einsatz von KI-Werkzeugen im Traffic-Prediction-Projekt:

- erhöhte die Entwicklungsgeschwindigkeit  
- unterstützte bei methodischen Fragestellungen  
- verbesserte Dokumentation und Verständlichkeit  
- ersetzte jedoch nicht die fachliche Bewertung  

Das Projekt bleibt eine eigenständig konzipierte, validierte und verantwortete Machine-Learning-Lösung zur Vorhersage von Verkehrsaufkommen.