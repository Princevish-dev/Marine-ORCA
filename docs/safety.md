# Safety Engine — ORCA

## Formula

```
SafetyScore =
  100
  - WindPenalty
  - WavePenalty
  - WarningPenalty
  - BoundaryPenalty
  + PFZBonus

Clamped: 0 ≤ SafetyScore ≤ 100
```

## Penalties

| Factor | Condition | Penalty |
|--------|-----------|---------|
| Wind | Light (<25 km/h) | 0 |
| Wind | Moderate (25–40) | 10 |
| Wind | High (40–60) | 20 |
| Wind | Extreme (>60) | 35 |
| Waves | Low (<1.5 m) | 0 |
| Waves | Moderate (1.5–2.5 m) | 12 |
| Waves | High (2.5–4.0 m) | 25 |
| Waves | Extreme (>4.0 m) | 40 |
| Warning | INFO | 5 |
| Warning | YELLOW | 15 |
| Warning | ORANGE | 35 |
| Warning | RED | 60 + critical override |
| Boundary | YELLOW | 8 |
| Boundary | ORANGE | 15 |
| Boundary | RED / Inside | 30–50 |

## PFZ Bonus

Maximum +10 points. Only when no RED/ORANGE critical override is active.

## Critical Override

If any active RED warning: score is capped at 30 regardless of other factors.
This ensures PFZ suitability never masks a genuine severe hazard.

## Labels

| Score | Label | Color |
|-------|-------|-------|
| 80–100 | EXCELLENT | #10b981 |
| 65–79 | GOOD | #22c55e |
| 50–64 | CAUTION | #eab308 |
| 35–49 | WARNING | #f97316 |
| 0–34 | CRITICAL | #ef4444 |
