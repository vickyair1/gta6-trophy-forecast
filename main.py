#!/usr/bin/env python3
"""GTA VI trophy rarity forecaster (gta6-trophy-rarity-forecast-01).

Reads every case file in $MAKEFUN_INPUT_DIR (default /input) and writes one
forecast per case to $MAKEFUN_OUTPUT_DIR (default /output).

Model, per case, from the case's own history of Exophase reads:

* Flat history (one distinct page state): Exophase has not refreshed, so the
  forecast is a refresh mixture. A refresh in the horizon is given a normal
  prior (mean 4.5 h, sd 1.0 h) conditioned on no refresh yet; when it comes,
  each rate drops by a factor of about 0.221 with lognormal jitter.
* Growth history (two or more distinct states): earn counts
  (rate * players_tracked / 100) and players_tracked are each fitted by OLS
  of their log against ln(1 + hours since launch), with the per-trophy slope
  shrunk toward its tier median and the global median. The forecast rate is
  the forecast count over the forecast player count, with a spread that
  combines the residual variance, the slope uncertainty and a random-walk
  term over the horizon.

Quantiles are written on the logit scale, rounded to 4 decimals (half-up),
clamped to [0.01, 99.99] and non-decreasing. Pure standard library, offline,
deterministic.
"""

import json
import math
import os
import statistics
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

EPOCH = datetime(2026, 11, 19, 0, 0, 0, tzinfo=timezone.utc)
Z = (-1.645, -0.674, 0.0, 0.674, 1.645)
ND = statistics.NormalDist()


def parse_time(text):
    """ISO 8601 UTC timestamp -> aware datetime."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def hours_since_epoch(when):
    return (when - EPOCH).total_seconds() / 3600.0


def log_time(when):
    """ln(1 + hours since launch), floored so it stays defined."""
    return math.log(max(1.0 + hours_since_epoch(when), 1e-9))


def logit(p):
    p = min(max(p, 0.01), 99.99)
    return math.log(p / (100.0 - p))


def inv_logit(l):
    if l >= 0:
        return 100.0 / (1.0 + math.exp(-l))
    e = math.exp(l)
    return 100.0 * e / (1.0 + e)


def round4(x):
    """Round to 4 decimals, half-up (like Math.round(x * 10000) / 10000)."""
    return float(Decimal(str(x)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def finish_quantiles(values):
    """Clamp to [0.01, 99.99], round to 4 decimals, enforce non-decreasing."""
    out = []
    prev = 0.01
    for v in values:
        q = round4(clamp(v, 0.01, 99.99))
        if q < prev:
            q = prev
        out.append(q)
        prev = q
    return out


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def ols(xs, ys):
    """Least squares of ys on xs. Returns (slope, intercept, resid_var, mean_x, sxx)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0.0:
        return 0.0, my, 0.0, mx, 0.0
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    intercept = my - slope * mx
    if n > 2:
        var = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys)) / (n - 2)
    else:
        var = 0.0
    return slope, intercept, var, mx, sxx


def median(values):
    vals = sorted(values)
    if not vals:
        return 0.0
    m = len(vals) // 2
    if len(vals) % 2:
        return vals[m]
    return 0.5 * (vals[m - 1] + vals[m])


def distinct_states(history):
    """Collapse consecutive reads with identical (players, rates) into one
    state, keeping the first read's time."""
    states = []
    for read in history:
        key = (read.get("players_tracked"), tuple(read.get("rates") or []))
        if states and states[-1][0] == key:
            continue
        states.append((key, parse_time(read["at"]), read))
    return states


def forecast_flat(case, state, checkpoint, horizon_h):
    """One distinct state: refresh-mixture forecast."""
    _, first_time, read = state
    last_rates = list(read.get("rates") or [])
    # A short rates list must never drop a trophy from the output: pad it.
    last_rates += [None] * (len(case["trophies"]) - len(last_rates))
    staleness = (checkpoint - first_time).total_seconds() / 3600.0
    # P(refresh in (S, S+H] | no refresh by S), refresh interval ~ N(4.5, 1.0).
    surv = 1.0 - norm_cdf(staleness - 4.5)
    if surv <= 1e-12:
        p_refresh = 0.90
    else:
        p_refresh = (norm_cdf(staleness + horizon_h - 4.5)
                     - norm_cdf(staleness - 4.5)) / surv
    p_refresh = clamp(p_refresh, 0.05, 0.90)
    drop = 0.221
    jitter = 0.20
    rows = []
    for trophy, rate in zip(case["trophies"], last_rates):
        tid = trophy["id"]
        if rate is None:
            rate = 0.0
        if rate >= 100.0:
            rows.append({"id": tid, "q": [100.0] * 5})
            continue
        qs = []
        for tau in (0.05, 0.25, 0.5, 0.75, 0.95):
            if tau < p_refresh:
                u = tau / p_refresh
                qs.append(drop * rate * math.exp(ND.inv_cdf(u) * jitter))
            else:
                qs.append(rate)
        rows.append({"id": tid, "q": finish_quantiles(qs)})
    return rows


def forecast_growth(case, states, checkpoint, horizon_min):
    """Two or more distinct states: count-based log-time growth."""
    horizon_h = horizon_min / 60.0
    d_days = horizon_min / 1440.0
    target = parse_time(case["target"])
    x_target = log_time(target)

    # Fit window: distinct states in the last 24 h before the checkpoint;
    # fall back to the last two states when that leaves fewer than two.
    cutoff = checkpoint.timestamp() - 24.0 * 3600.0
    fit = [s for s in states if s[1].timestamp() >= cutoff]
    if len(fit) < 2:
        fit = states[-2:]
    n = len(fit)
    xs = [log_time(s[1]) for s in fit]
    x_last = xs[-1]
    # Carry the last known positive player count forward over any read that
    # lacks one, so a 0/missing count can never zero out the earn counts.
    players = []
    last_known = 1
    for s in fit:
        p = s[2].get("players_tracked") or 0
        if p > 0:
            last_known = p
        players.append(last_known)
    n_last = players[-1]

    # Players: OLS of ln(N) on log-time, shrunk toward zero growth.
    b_n, _, _, _, _ = ols(xs, [math.log(max(p, 1)) for p in players])
    b_n = clamp(b_n * n / (n + 12.0), -0.8, 0.8)
    n_target = max(n_last * math.exp(b_n * (x_target - x_last)), float(n_last))

    nt = len(case["trophies"])
    # First pass: per-trophy OLS slopes on log counts.
    slopes = []
    fits = []
    for i in range(nt):
        pts = []
        for j, s in enumerate(fit):
            rate = (s[2].get("rates") or [None] * nt)[i]
            if rate is not None:
                pts.append((xs[j], rate * players[j] / 100.0))
        if len(pts) < 2:
            fits.append(None)
            slopes.append(None)
            continue
        px = [p[0] for p in pts]
        py = [math.log(p[1] + 0.5) for p in pts]
        b, _, var, mx, sxx = ols(px, py)
        slopes.append(b)
        fits.append((pts, b, var, mx, sxx, len(pts)))
    usable = [b for b in slopes if b is not None]
    global_med = median(usable)
    tier_med = {}
    for tier in {t["tier"] for t in case["trophies"]}:
        vals = [slopes[i] for i, t in enumerate(case["trophies"])
                if t["tier"] == tier and slopes[i] is not None]
        tier_med[tier] = median(vals) if vals else global_med

    rows = []
    for i, trophy in enumerate(case["trophies"]):
        tid = trophy["id"]
        rates = [(s[2].get("rates") or [None] * nt)[i] for s in states]
        last_rate = next((r for r in reversed(rates) if r is not None), 0.0)
        if last_rate >= 100.0:
            rows.append({"id": tid, "q": [100.0] * 5})
            continue
        fit_i = fits[i]
        if fit_i is None:
            med = last_rate
            sigma = 0.5 * math.sqrt(d_days) + 0.3
        else:
            pts, b, var, mx, sxx, ni = fit_i
            w = ni / (ni + 3.0)
            b1 = w * b + (1.0 - w) * tier_med[trophy["tier"]]
            b2 = 0.85 * b1 + 0.15 * global_med
            b_shrunk = clamp(b2 * ni / (ni + 8.0), -1.2, 1.2)
            c_last = pts[-1][1]
            c_target = c_last * math.exp(b_shrunk * (x_target - pts[-1][0]))
            med = 100.0 * c_target / n_target
            if trophy["tier"] == "platinum":
                med = min(med, 5.0)
            else:
                med = min(med, 95.0)
            med = max(med, 0.01)
            if sxx > 0.0:
                slope_var = var * (1.0 + 1.0 / ni + (x_target - mx) ** 2 / sxx)
            else:
                slope_var = var
            sigma = math.sqrt(0.09 * d_days + max(var, 0.09) + 0.04
                              + 0.25 * slope_var)
            sigma = clamp(sigma, 0.35, 1.3)
        base = logit(med)
        rows.append({"id": tid,
                     "q": finish_quantiles([inv_logit(base + z * sigma) for z in Z])})
    return rows


def forecast_case(case):
    checkpoint = parse_time(case["at"])
    horizon_min = float(case["horizon_minutes"])
    horizon_h = horizon_min / 60.0
    states = distinct_states(case.get("history") or [])
    if not states:
        return [{"id": t["id"], "q": [0.01] * 5} for t in case["trophies"]]
    if len(states) == 1:
        return forecast_flat(case, states[0], checkpoint, horizon_h)
    return forecast_growth(case, states, checkpoint, horizon_min)


def main():
    in_dir = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    for name in sorted(os.listdir(in_dir)):
        if not name.endswith(".in"):
            continue
        with open(os.path.join(in_dir, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        rows = forecast_case(case)
        payload = {"trophies": rows}
        out_name = name[:-3] + ".out"
        with open(os.path.join(out_dir, out_name), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
