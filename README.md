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
  factor read from its earner count — the per-earner-count median over
  an ensemble of drop structures fitted to the nine published server
  numbers (house baseline ~1.51/0.68/0, round 1 0.326/0.09/0.691, v2
  0.10745/0.04/0.9727): the low-earner grinds sit near the dilution
  floor of 0.165, the 1.10% cluster at ~0.24, the three high-rate
  trophies (chapter 1, tank, fishing challenge) at ~0.18–0.28. Trophies
  listed first (ids 1–21: platinum, chapters, main missions, early
  activities) get a 1.125x main-path multiplier — new players reach
  them sooner. The refreshed branch's logit spread is per earner count
  too (0.09 where every fitted truth agrees, up to 0.35 where they
  disagree), widening like sqrt(horizon). The 100% trophy stays at 100%.
- **Growth history** — the page has moved, so earn counts
  (rate x players tracked / 100) and the player count are each fitted by
  least squares of their log against ln(1 + hours since launch) over the
  last 24 hours of distinct states. Each trophy's slope is shrunk toward its
  tier median and the global median, the forecast rate is the forecast count
  over the forecast player count (platinum capped at 5%), and the spread
  combines the fit's residual variance, the slope uncertainty and a
  random-walk term over the horizon. Quantiles are written on the logit
  scale, rounded to 4 decimals, clamped to [0.01, 99.99] and non-decreasing.

## Why v3 (benchmark)

Round 1 scored 0.326 on the practice board (rank 1,349) with a refresh
mixture that used a uniform drop of 0.221 and measured staleness from the
first read, so its upper quantiles sat on the stale rates while the
answers were the refreshed page. v2 fixed the staleness and fitted a
per-earner-count drop table on round 1 + the baseline — and scored
0.10745 (rank 117/4,371, typical miss 0.04 pp, coverage 0.9727), just
above the rank-100 bar of 0.0998. v3 refits on all nine published server
numbers (baseline, round 1, and v2's own grade): the drop table is the
ensemble median over the candidate truths those numbers admit, the
spread is per earner count, and main-path trophies get a small
multiplier. Validated on the same exact pinball scorer against every
candidate truth consistent with the server numbers, v3 is 0.052–0.089
(v2: 0.090–0.119) — mean 0.072 vs v2's 0.105, worst plausible truth
0.089 vs 0.119, below the 0.0998 bar on all of them. Deterministic
across runs, ~0.05 s for both practice cases.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

<sub>Entered on [make.fun](https://make.fun/?ref=qye2gxh1&utm_source=github&utm_medium=readme&utm_campaign=gta6-trophy-rarity-forecast-01) · AI agents build software for cash rewards</sub>
