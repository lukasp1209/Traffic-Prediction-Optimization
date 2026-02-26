# agents.md

## Projekt: Traffic Prediction & Optimization

Dieses Dokument beschreibt, wie (AI-)Agents in diesem Repository arbeiten sollen: Ziele, Regeln, Abläufe, Definition of Done und Qualitätschecks. Es ist bewusst praxisnah gehalten, damit Änderungen konsistent, nachvollziehbar und reproduzierbar bleiben.

---

## 1) Ziel & Scope

**Ziel:** Kurzfristige Vorhersage von Verkehrsaufkommen (Zeitreihe, stündlich) inkl. Feature Engineering, Modellvergleich und Evaluation.

**In Scope**
- EDA (Explorative Datenanalyse) und Datenqualitätschecks
- Feature Engineering für Zeitreihen (z. B. zyklische Zeitfeatures, Lags, Rolling Statistics)
- Chronologischer Train/Test-Split (Leakage vermeiden)
- Modelltraining & Vergleich (Baseline → stärkere Modelle)
- Evaluation (MAE, RMSE, MAPE) + Residualanalyse
- Reproduzierbarkeit (Seeds, saubere Notebooks)

**Out of Scope (ohne explizite Anforderung)**
- Produktiv-Deployment / MLOps-Infrastruktur
- Webapp-Implementierung (nur Konzept/Skizze)
- Nutzung externer Datenquellen ohne klare Freigabe/Quelle

---

## 2) Repository-Konventionen

### Notebook-Workflow
- Änderungen bevorzugt **in Notebooks** (Jupyter) oder zusätzlich als **.py Utility** (wenn Code wiederverwendbar wird).
- Jede Notebook-Sektion soll:
  1. *Ziel* (kurzer Satz)
  2. *Methode*
  3. *Ergebnis/Interpretation*
  enthalten.

### Namensgebung
- Zeitstempelspalte: `ds` (datetime)
- Zielvariable: `y`
- Kalendarische Features: `hour`, `weekday`, `month`, ggf. `is_weekend`
- Zyklische Features: `hour_sin`, `hour_cos`
- Lag Features: `lag_1`, `lag_24` (oder konsistentes Schema `lag_{k}`)
- Rolling Features: `rolling_mean_3h`, `rolling_mean_12h` (oder Schema `rolling_mean_{k}h`)

### Reproduzierbarkeit
- Setze Seeds (`numpy.random.seed(...)`) bei Simulation/Randomness.
- Dokumentiere Versionen/Abhängigkeiten nur, wenn nötig (z. B. bei Inkompatibilitäten).

---

## 3) Daten- & Leakage-Regeln (Zeitreihe!)

**Grundsatz:** Bei Zeitreihen ist Data Leakage der häufigste Fehler.

- **Split immer chronologisch**: Train vor Test.
- **Feature Engineering mit Shift**:
  - Lags und Rolling-Werte dürfen nur Vergangenheitswerte verwenden.
  - Rolling-Fenster: i. d. R. mit `shift(1)` vor `rolling(...)`.
- **Keine Aggregationen über die Zukunft** (z. B. “Monatsmittelwert” aus gesamten Daten als Feature).

Checkliste (vor Modelltraining):
- [ ] Gibt es Features, die indirekt `y` aus der Zukunft enthalten könnten?
- [ ] Wurde für Rolling-Features korrekt geshiftet?
- [ ] Wurde der Split vor modellabhängigen Transformationen durchgeführt (wenn relevant)?

---

## 4) Standard-ML-Pipeline (empfohlen)

### Schritt A — Baseline & Setup
- Naive Baseline (z. B. `y_hat = lag_1` oder “letzte 24h”) als Referenz.
- Dann einfache Modelle (Lineare Regression) als zweite Referenz.

### Schritt B — Feature Engineering
- Zyklisch: `hour_sin`, `hour_cos`
- Kalender: `weekday`, `is_weekend`, `month`
- Lags: `lag_1`, `lag_24` (optional mehr)
- Rolling: `rolling_mean_3h`, `rolling_mean_12h`
- Kategorial: `weather` via One-Hot-Encoding (nur wenn vorhanden/benötigt)

### Schritt C — Split
- Chronologischer Train/Test-Split (z. B. letzte x% als Test).
- Optional: Walk-forward/TimeSeries CV (wenn gefordert).

### Schritt D — Modelle
Empfohlene Reihenfolge:
1. Baseline (naiv)
2. Lineare Regression
3. Random Forest / Gradient Boosting
4. Spezielle Zeitreihenmodelle (nur bei Bedarf/Setup): Prophet
5. Deep Learning (nur bei klarem Mehrwert): LSTM

### Schritt E — Evaluation
- Primärmetriken: **MAE, RMSE, MAPE**
- Zusätzlich:
  - Plot: Ist vs. Prognose (Zeitachse)
  - Residuenplot (Zeit / Histogramm)
  - Fehler nach Stunde/Wochentag (um Muster zu erkennen)

---

## 5) Qualitätsstandards (Definition of Done)

Eine Änderung gilt als “fertig”, wenn:

**Funktional**
- [ ] Notebook läuft von oben nach unten ohne Fehler.
- [ ] Ergebnisse sind plausibel und kommentiert (kurze Interpretation).

**ML-Qualität**
- [ ] Kein Data Leakage erkennbar.
- [ ] Chronologischer Split ist dokumentiert.
- [ ] Baseline-Ergebnis vorhanden (damit Fortschritt messbar ist).

**Lesbarkeit**
- [ ] Überschriften/Abschnitte sind nachvollziehbar.
- [ ] Plots haben Titel, Achsenbeschriftungen, ggf. Legenden.
- [ ] Variablennamen sind konsistent.

---

## 6) Agent-Verhalten: Arbeitsweise & Kommunikation

Wenn ein Agent eine Aufgabe bearbeitet, soll er:

1. **Klärungsfragen stellen**, wenn Anforderungen unklar sind (z. B. “welches Modell genau?”, “welcher Split?”).
2. **Kleinste sinnvolle Änderungen** bevorzugen (kein unnötiges Refactoring).
3. **Jede Modell-/Feature-Entscheidung kurz begründen** (1–2 Sätze reichen).
4. **Ergebnisse messen** (mindestens eine Metrik + Baseline).

---

## 7) Sicherheits- & Datenschutzregeln

- Keine echten Zugangsdaten, Tokens, Keys etc. in Notebooks/Repo ablegen.
- Falls Konfiguration nötig: nur Platzhalter verwenden (z. B. `<API_KEY>`).
- Externe Datenquellen nur mit klarer Quelle/Einwilligung verwenden.

---

## 8) Nächste sinnvolle Erweiterungen (optional)

- Walk-forward Validation für robustere Schätzung.
- Feature Importance / Permutation Importance bei Tree-Modellen.
- Fehleranalyse nach Wetter/Feiertag/Wochenende.
- Modellkalibrierung/Intervalle (Prediction Intervals) für operativen Nutzen.

---