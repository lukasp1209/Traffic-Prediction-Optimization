# Model Card

## Modell
- Name: RandomForest
- Anwendungsfall: Kurzfristige Verkehrsprognose (Stundenebene)

## Trainingskontext
- Datensätze: 8734
- Train/Test: 6987 / 1747 (chronologisch)

## Kernmetriken (Test)
- MAE: 4874.081
- RMSE: 6807.078
- R2: 0.9598

## Grenzen
- Synthetische Anteile möglich (abhängig von U-Phase-Konfiguration)
- Externe Ereignisse (Unfälle, Großevents, Baustellen) nur begrenzt abgebildet
- Regelmäßige Validierung auf Live-Daten erforderlich