# Glossar & Begriffserklärungen  
## 🚦 Projekt: Traffic Prediction & Optimization

Dieses Glossar erläutert zentrale Begriffe, Methoden und Kennzahlen des Projekts **Traffic Prediction** in klarer, allgemeinverständlicher Sprache.  
Es richtet sich an Leserinnen und Leser ohne vertiefte Data-Science-Vorkenntnisse und dient als kompaktes Nachschlagewerk.

---

## 1. Verkehrsbezogene Begriffe

### Verkehrsaufkommen (Traffic Volume)
Anzahl der Fahrzeuge, die einen definierten Straßenabschnitt in einem festgelegten Zeitraum passieren (z. B. pro Stunde).  
Im Projekt ist das Verkehrsaufkommen die **Zielvariable** (Target Variable), die prognostiziert werden soll.

**Typische Einheit:** Fahrzeuge pro Zeiteinheit (z. B. Fahrzeuge/Stunde)

---

### Spitzenstunde (Peak Hour)
Zeiträume mit besonders hohem Verkehrsaufkommen, häufig verursacht durch Berufs- und Schulverkehr.

**Typische Beispiele (regional unterschiedlich):**
- morgens ca. 07:00–09:00 Uhr  
- nachmittags/abends ca. 16:00–18:00 Uhr

**Relevanz für Modelle:**  
Spitzenstunden sind oft stark wiederkehrend (tägliche Saisonalität) und können durch Feiertage oder Ferien deutlich abweichen.

---

### Wochenend-Effekt
Systematischer Unterschied im Verkehrsaufkommen zwischen Werktagen und Wochenenden.

**Häufige Beobachtungen:**
- insgesamt geringeres Aufkommen
- gleichmäßigere Verteilung über den Tag
- weniger ausgeprägte Pendler-Spitzen

**Relevanz:**  
Kalenderfeatures (Wochentag, Wochenende ja/nein) erhöhen die Prognosequalität oft deutlich.

---

### Saisonalität
Wiederkehrende Muster in einer Zeitreihe.

**Im Verkehrskontext häufig:**
- **Tägliche Saisonalität:** morgendliche und abendliche Peaks  
- **Wöchentliche Saisonalität:** Werktage vs. Wochenende  
- **Jährliche/seasonale Effekte:** Ferienzeiten, saisonales Mobilitätsverhalten, Feiertage (ggf. auch Wetter)

**Abgrenzung:**  
Saisonalität ist **regelmäßig wiederkehrend**; einmalige Ereignisse (z. B. ein Unfall) zählen nicht dazu.

---

### Trend
Langfristige, gerichtete Veränderung des Verkehrsaufkommens über einen längeren Zeitraum (z. B. über Monate).

**Beispiele:**
- Zunahme durch Bevölkerungswachstum
- Abnahme durch Baustellenumleitungen oder neue ÖPNV-Angebote

---

### Ausreißer (Outlier)
Ungewöhnlich hohe oder niedrige Messwerte im Vergleich zum typischen Muster.

**Mögliche Ursachen:**
- Unfälle, Baustellen, Großveranstaltungen
- extreme Wetterereignisse
- Messfehler oder Datenlücken

**Relevanz:**  
Ausreißer können Modelle verzerren und sollten in der Datenanalyse (EDA) sichtbar gemacht und ggf. behandelt werden (z. B. Korrektur, Markierung, robuste Modelle).

---

## 2. Daten- und Zeitreihenbegriffe

### Zeitreihe (Time Series)
Chronologisch geordnete Abfolge von Messwerten.  
Im Projekt: Verkehrsaufkommen über Stunden, Tage oder längere Zeiträume.

**Wichtig:**  
Die zeitliche Reihenfolge trägt Information. Daher werden Daten bei Zeitreihen nicht „beliebig gemischt“.

---

### Zeitauflösung / Granularität
Der zeitliche Abstand zwischen zwei Messpunkten.

**Beispiele:** 5 Minuten, 15 Minuten, 1 Stunde, 1 Tag  
**Auswirkung:** Je feiner die Auflösung, desto detaillierter die Muster – aber auch desto mehr Rauschen und potenziell fehlende Werte.

---

### Datenleck (Data Leakage)
Unzulässige Nutzung von Informationen, die zum Vorhersagezeitpunkt in der Realität noch nicht verfügbar wären.

**Typisches Risiko bei Zeitreihen:**  
Zufälliges Mischen von Train- und Testdaten kann dazu führen, dass „Zukunft“ im Training landet und das Modell dadurch zu optimistisch bewertet wird.

---

## 3. Machine Learning & Feature Engineering

### Prognose (Forecasting)
Vorhersage zukünftiger Werte auf Basis historischer Daten und ggf. externer Einflussfaktoren.

**Beispielfrage:**  
„Wie hoch ist das Verkehrsaufkommen morgen um 08:00 Uhr?“

---

### Feature (Merkmal)
Eingangsvariable, die ein Modell zur Vorhersage nutzt.

**Beispiele im Projekt:**
- Stunde des Tages, Wochentag, Monat
- Wochenende/Feiertag-Indikator
- vergangene Verkehrsaufkommen (Lag-Features)
- gleitende Statistiken (Rolling Features)

---

### Zielvariable (Target Variable)
Die Größe, die vorhergesagt werden soll.  
Im Projekt: typischerweise das Verkehrsaufkommen (`y`).

---

### Lag-Feature (Verzögerungsmerkmal)
Vergangenheitswert(e), die als Feature verwendet werden.

**Typische Lags:**
- `t-1` (eine Stunde zuvor)
- `t-24` (gleiche Uhrzeit am Vortag)
- `t-168` (gleiche Uhrzeit in der Vorwoche bei stündlichen Daten)

**Warum wichtig?**  
Verkehr ist stark von kurz- und mittelfristigen historischen Verläufen abhängig.

---

### Rolling Features (Gleitende Kennzahlen)
Statistiken, die über ein gleitendes Zeitfenster berechnet werden, um kurzfristige Schwankungen zu glätten oder lokale Muster abzubilden.

**Beispiele:**
- **Rolling Mean:** Durchschnitt der letzten 3/24 Stunden  
- **Rolling Std:** Streuung im gleichen Fenster (Hinweis auf „Unruhe“ im Verkehr)

---

### One-Hot-Encoding
Umwandlung kategorialer Merkmale (z. B. Wochentag) in binäre Indikatorvariablen, die viele ML-Modelle besser verarbeiten können.

---

### Overfitting (Überanpassung)
Das Modell passt sich zu stark an die Trainingsdaten an und generalisiert schlecht auf neue Daten.

**Anschaulich:**  
Wie jemand, der alte Prüfungen auswendig lernt, aber neue Aufgaben nicht lösen kann.

**Typische Gegenmaßnahmen:**
- einfachere Modelle / Regularisierung
- mehr Trainingsdaten
- sauberer Zeitreihen-Split, Cross-Validation
- Feature-Auswahl und robuste Validierung

---

### Underfitting (Unteranpassung)
Das Modell ist zu simpel, um die vorhandenen Muster zu lernen (z. B. Tages- und Wochenzyklen).  
Ergebnis: systematische Fehler und schwache Prognosequalität.

---

## 4. Modelltraining, Validierung und Splits

### Trainingsdaten (Train Set)
Datenbereich, auf dem das Modell die Zusammenhänge lernt.

---

### Testdaten (Test Set)
Unabhängiger Datenbereich zur abschließenden Bewertung der Modellgüte auf „unbekannten“ Daten.

**Wichtig bei Zeitreihen:**  
Train liegt zeitlich **vor** Test.

---

### Validierungsdaten (Validation Set)
Zusätzlicher Datenbereich zur Modell- und Hyperparameterwahl, ohne den Testbereich zu „verbrauchen“.

---

### Zeitreihen-konforme Cross-Validation (Rolling / Expanding Window)
Validierungsverfahren für Zeitreihen, bei dem wiederholt auf einem wachsenden (oder rollenden) Zeitfenster trainiert und auf dem jeweils nachfolgenden Zeitraum getestet wird.

**Ziel:**  
Robuste Einschätzung der Modellleistung über verschiedene Zeitabschnitte hinweg.

---

## 5. Bewertungsmetriken (Regression)

### MAE (Mean Absolute Error)
Durchschnitt der absoluten Abweichungen zwischen Prognose und Ist-Wert.

**Interpretation:**  
Ein MAE von 5 bedeutet: Die Prognose liegt im Mittel um **5 Fahrzeuge** daneben (bei entsprechender Einheit).

**Eigenschaft:**  
Gut interpretierbar und weniger empfindlich gegenüber einzelnen sehr großen Fehlern als RMSE.

---

### RMSE (Root Mean Squared Error)
Wurzel des mittleren quadratischen Fehlers. Große Fehler werden stärker gewichtet.

**Wann sinnvoll?**  
Wenn starke Fehlprognosen besonders kritisch sind (z. B. Kapazitätsplanung, Stauwarnungen).

---

### R² (Bestimmtheitsmaß)
Maß dafür, wie viel Varianz der Zielvariable durch das Modell erklärt wird.

**Typischer Wertebereich:** 0 bis 1 (kann in Sonderfällen auch negativ sein)  
- nahe 1: sehr gute Erklärung der Schwankungen  
- nahe 0: geringe Erklärungskraft

**Hinweis:**  
R² ist hilfreich zum Modellvergleich, sollte aber immer zusammen mit MAE/RMSE und einer visuellen Prüfung betrachtet werden.

---

## 6. Projektprozess (Data Workflow)

### 1) Problemdefinition
Klärung der Aufgabe und des Prognosehorizonts.

**Beispiel:**  
Vorhersage des Verkehrsaufkommens der nächsten 24 Stunden (stündlich).

---

### 2) Datenverständnis & EDA (Explorative Datenanalyse)
Ziel: Muster, Datenqualität und Auffälligkeiten erkennen.

**Typische Analysen:**
- Zeitreihenplots (Trend, Saisonalität, Ausreißer)
- Heatmaps (Stunde × Wochentag)
- Verteilungen/Boxplots (z. B. Wochenend-Effekt)
- Prüfung auf fehlende Werte und Inkonsistenzen

---

### 3) Datenaufbereitung
Bereinigung und Strukturierung der Daten.

**Beispiele:**
- Umgang mit fehlenden Werten
- einheitliche Zeitstempel und Frequenzen
- ggf. Skalierung/Transformationen

---

### 4) Feature Engineering
Erzeugung zusätzlicher Merkmale zur besseren Modellierbarkeit.

**Beispiele:**
- Kalenderfeatures (Stunde, Wochentag, Monat)
- Lag-Features, Rolling Features
- externe Features (Feiertage, Wetter), sofern verfügbar

---

### 5) Modellierung
Training und Vergleich verschiedener Modellklassen.

**Mögliche Ansätze (beispielhaft):**
- lineare Modelle als Baseline (interpretierbar)
- Baum-Ensembles (z. B. Random Forest, Gradient Boosting) für Nichtlinearitäten
- spezialisierte Zeitreihenmodelle (z. B. SARIMA/Prophet), falls eingesetzt
- Deep Learning (z. B. LSTM), optional bei komplexen Abhängigkeiten

---

### 6) Evaluation & Modellvergleich
Bewertung anhand:
- MAE, RMSE, R²
- Stabilität über Zeit (z. B. mehrere CV-Splits)
- visueller Vergleich Ist vs. Prognose
- Plausibilitätschecks (Feiertage, Peaks, Wochenenden)

---

### 7) Anwendung / Deployment (optional)
Integration in eine produktive Umgebung.

**Beispiele:**
- Dashboard zur Visualisierung
- API für Prognoseabrufe
- Entscheidungsunterstützung für Verkehrsmanagement

---

## 7. Ziel und Kernaussage des Projekts

### Ziel
- Verkehrsflüsse besser verstehen und vorhersagen  
- Staus frühzeitig erkennen und Maßnahmen ableiten  
- Infrastruktur und Ressourcen effizient planen  
- potenziell Emissionen reduzieren und Mobilität verbessern  

---

### Kernaussage
Verkehrsdaten zeigen häufig **stabile, wiederkehrende Muster** (Tageszeit, Wochentag, saisonale Effekte).  
Diese Struktur macht Verkehrsprognosen gut modellierbar – vorausgesetzt, **Saisonalität, zeitliche Abhängigkeiten und eine zeitreihen-konforme Validierung** werden konsequent berücksichtigt.