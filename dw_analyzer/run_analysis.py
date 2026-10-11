"""Run analysis for the PDF: Python mirror of report/static/analysis.js (per-run extras, angle bins, HR zones, correlations)."""
import math

import numpy as np

from dw_analyzer.metrics import HR_ZONES_PCT

# Variables in the correlation matrix: (row key, short label); same order as CORR_VARS in report.js
CORR_VARS = [
    ("run", "Run #"), ("pace_s_per_km", "Pace"), ("duration_s", "Duration"), ("distance_m", "Distance"),
    ("max_speed_kmh", "Max 5 s"), ("angle_off_deg", "Off downwind"), ("vmg_kmh", "VMG"), ("hr_avg", "HR avg"),
    ("hr_max", "HR max"), ("back_up_s", "Back up"), ("hr_peak_after", "HR peak after"), ("hr_drop_60s", "HR drop 60 s"),
]


def _ok(v) -> bool:
    return v is not None and bool(np.isfinite(v))


def _num(v):
    """Finite number as float, else None (NaN and None both mean missing)."""
    return float(v) if _ok(v) else None


def pearson(xs, ys):
    """Pearson r; None for fewer than 3 pairs or a constant variable."""
    x, y = np.asarray(xs, float), np.asarray(ys, float)
    if len(x) < 3:
        return None
    dx, dy = x - x.mean(), y - y.mean()
    sxx, syy = float(dx @ dx), float(dy @ dy)
    return float(dx @ dy) / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def lin_fit(xs, ys):
    """Least-squares y on x as (slope, intercept); None for fewer than 2 points or constant x."""
    x, y = np.asarray(xs, float), np.asarray(ys, float)
    if len(x) < 2:
        return None
    dx = x - x.mean()
    sxx = float(dx @ dx)
    if not sxx > 0:
        return None
    slope = float(dx @ (y - y.mean())) / sxx
    return slope, float(y.mean()) - slope * float(x.mean())


def run_extras(track, runs, rows) -> None:
    """Add prev_duration_s, prev_distance_m, prev_hr_max, hr_peak_after, hr_drop_60s and efficiency to rows in place."""
    hr = track["hr"].to_numpy(float)
    n = len(hr)
    for i, row in enumerate(rows):
        prev = rows[i - 1] if i else None
        row["prev_duration_s"] = _num(prev["duration_s"]) if prev else None
        row["prev_distance_m"] = _num(prev["distance_m"]) if prev else None
        row["prev_hr_max"] = _num(prev["hr_max"]) if prev else None
        nxt = runs[i + 1].start if i + 1 < len(runs) else None
        stop = min(runs[i].end + 60, n if nxt is None else nxt, n)
        window = hr[runs[i].end:stop] if stop > runs[i].end else hr[:0]
        peak_idx = None
        if np.isfinite(window).any():
            peak_idx = runs[i].end + int(np.nanargmax(window))  # first maximum
        row["hr_peak_after"] = None if peak_idx is None else float(hr[peak_idx])
        after = None if peak_idx is None else peak_idx + 60
        row["hr_drop_60s"] = None if (after is None or after >= n or (nxt is not None and after >= nxt)
                                      or not np.isfinite(hr[after])) else float(hr[peak_idx] - hr[after])
        hr_avg, speed = _num(row.get("hr_avg")), _num(row.get("avg_speed_kmh"))
        row["efficiency"] = speed / hr_avg * 100 if hr_avg and hr_avg > 0 and speed is not None else None


def angle_bins(track, runs, bin_deg=5, min_samples=5) -> list[dict]:
    """Speed per signed angle-off-downwind bin inside the runs (gaps excluded): dicts of angle, avg, best, vmg, n."""
    speed = track["speed_kmh"].to_numpy(float)
    angle = track["angle_off_deg"].to_numpy(float)
    gap = track["gap"].to_numpy(bool)
    inside = np.zeros(len(track), bool)
    for run in runs:
        inside[run.start:run.end] = True
    use = inside & ~gap & np.isfinite(speed) & np.isfinite(angle)
    centre = np.floor(angle[use] / bin_deg) * bin_deg + bin_deg / 2
    out = []
    for c in np.unique(centre):
        s = speed[use][centre == c]
        if len(s) >= min_samples:
            avg = float(s.sum() / len(s))
            out.append({"angle": float(c), "avg": avg, "best": float(s.max()),
                        "vmg": avg * math.cos(math.radians(c)), "n": int(len(s))})
    return out


def zone_time(hr, runs, max_hr) -> dict:
    """Percent of samples with HR per zone Z0-Z5, inside the runs ("foiling") and over the whole session."""
    zeros = [0.0] * 6
    if not max_hr > 0:
        return {"foiling": list(zeros), "session": list(zeros)}
    hr = np.asarray(hr, float)
    inside = np.zeros(len(hr), bool)
    for run in runs:
        inside[run.start:run.end] = True
    have = np.isfinite(hr)
    zone = np.searchsorted(HR_ZONES_PCT, hr[have] / max_hr * 100, side="right")  # count of bounds <= pct

    def share(mask):
        counts = np.bincount(zone[mask], minlength=6).astype(float)
        total = counts.sum()
        return (counts / total * 100).tolist() if total else list(zeros)

    return {"foiling": share(inside[have]), "session": share(np.ones(len(zone), bool))}


def corr_matrix(rows):
    """Pairwise-complete Pearson r over CORR_VARS: (labels, z with None where undefined, n pairs per cell)."""
    z, ns = [], []
    for a, _ in CORR_VARS:
        z_row, n_row = [], []
        for b, _ in CORR_VARS:
            both = [(_num(r.get(a)), _num(r.get(b))) for r in rows]
            both = [p for p in both if p[0] is not None and p[1] is not None]
            z_row.append(pearson([p[0] for p in both], [p[1] for p in both]))
            n_row.append(len(both))
        z.append(z_row)
        ns.append(n_row)
    return [label for _, label in CORR_VARS], z, ns
