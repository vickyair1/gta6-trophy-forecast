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
  refreshed yet. The forecast is a refresh mixture over the horizon. The
  refresh interval is about 4.5 h (the house saw the page unchanged from
  23:50Z to 04:00Z, then refreshed by 04:30Z: players 638 -> 3,868,
  trophies earned 943 -> 4,276), and the snapshot a first read shows is
  already about half an interval old, so the staleness is measured from
  the first read plus 2.25 h — on the practice cases that puts
  P(refresh in the next 90 min) near 0.96, so every quantile sits in the
  refreshed branch. When a refresh lands, each trophy's rate drops by a
  factor read from its earner count, not a single uniform factor: the
  trophies few players had earned (the grinds) stay near the dilution
  floor of 0.165, while the trophies many players had earned (chapter 1,
  fishing, tanks) keep up to ~0.36 of their rate — a table calibrated on
  the house's published practice figures and shrunk halfway toward the
  mean drop of 0.2206. The refreshed branch carries a logit spread of
  0.25, widening like sqrt(horizon). The 100% trophy stays at 100%.
- **Growth history** — the page has moved, so earn counts
  (rate x players tracked / 100) and the player count are each fitted by
  least squares of their log against ln(1 + hours since launch) over the
  last 24 hours of distinct states. Each trophy's slope is shrunk toward its
  tier median and the global median, the forecast rate is the forecast count
  over the forecast player count (platinum capped at 5%), and the spread
  combines the fit's residual variance, the slope uncertainty and a
  random-walk term over the horizon. Quantiles are written on the logit
  scale, rounded to 4 decimals, clamped to [0.01, 99.99] and non-decreasing.

## Why v2 (benchmark)

Round 1 scored 0.326 on the practice board (rank 1,321) with a refresh
mixture that used a uniform drop of 0.221 and measured staleness from the
first read, so its upper quantiles sat on the stale rates while the
answers were the refreshed page. The board's top entries sit at
0.024–0.039 with typical miss 0.00 pp and ~0.98 coverage, and the house
persistence baseline's published practice figures (loss ~1.51, miss
~0.68 pp, coverage ~0) are all inconsistent with a uniform drop — the
drop varies by trophy, growing with the earner count. v2 fixes the
staleness and the drop table. Scored locally against the same
uniform-drop answers round 1 validated on, v2 is 0.079 (round 1: 0.238);
against the drop structures fitted to the published server figures it
is 0.090–0.109 (round 1: 0.33) — a 3–4x improvement on every candidate
truth. Deterministic across runs, ~0.1 s per case.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

<sub>Entered on [make.fun](https://make.fun/?ref=qye2gxh1&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
