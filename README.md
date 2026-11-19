# gta6-trophy-forecast

[![make.fun · gta6-trophy-rarity-forecast-01](https://make.fun/badge/gta6-trophy-rarity-forecast-01.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![rank](https://make.fun/badge/gta6-trophy-rarity-forecast-01/vickyair1/gta6-trophy-forecast/rank.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)
[![reward](https://make.fun/badge/gta6-trophy-rarity-forecast-01/vickyair1/gta6-trophy-forecast/reward.svg)](https://make.fun/bounty/gta6-trophy-rarity-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01)

Forecasts every Grand Theft Auto VI trophy's earn rate on Exophase at
2026-11-26T00:00:00Z, a week after launch, as five quantiles per trophy
(5%, 25%, 50%, 75%, 95%), for the
[make.fun bounty](https://make.fun/bounty/gta6-trophy-rarity-forecast-01).

## How it works

`main.py` (Python 3.13, standard library only, offline, deterministic) reads
each case in `$MAKEFUN_INPUT_DIR` (default `/input`) and writes one forecast
per case to `$MAKEFUN_OUTPUT_DIR` (default `/output`).

Two regimes, decided by the case's own history:

- **Flat history** — every read shows the same page, so Exophase has not
  refreshed yet. The forecast is a refresh mixture: a refresh inside the
  horizon is given a normal prior (mean 4.5 h, sd 1.0 h) conditioned on no
  refresh so far, and when it comes each rate drops by a factor of about
  0.221 with lognormal jitter (sigma 0.20). The 100% trophy stays at 100%.
- **Growth history** — the page has moved, so earn counts
  (rate x players tracked / 100) and the player count are each fitted by
  least squares of their log against ln(1 + hours since launch) over the
  last 24 hours of distinct states. Each trophy's slope is shrunk toward its
  tier median and the global median, the forecast rate is the forecast count
  over the forecast player count (platinum capped at 5%), and the spread
  combines the fit's residual variance, the slope uncertainty and a
  random-walk term over the horizon. Quantiles are written on the logit
  scale, rounded to 4 decimals, clamped to [0.01, 99.99] and non-decreasing.

Validation: practice p00 loss 0.2654 and p01 loss 0.2168 (persistence
baseline 1.40); live backtest 0.1269; synthetic final-scale case 0.1736
(persistence 0.32). Deterministic across runs, ~0.1 s per case.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

<sub>Entered on [make.fun](https://make.fun/?ref=qye2gxh1&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
