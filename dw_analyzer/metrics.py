"""Session, split and run statistics on a prepared 1 Hz track."""
import numpy as np
import pandas as pd

from dw_analyzer.angles import circ_mean_deg, signed_diff_deg

NAN = float("nan")


def add_vmg(track: pd.DataFrame, downwind_deg: float) -> pd.DataFrame:
    out = track.copy()
    out["angle_off_deg"] = signed_diff_deg(out["heading_deg"].to_numpy(), downwind_deg)
    out["vmg_kmh"] = out["speed_kmh"] * np.cos(np.radians(out["angle_off_deg"]))
    return out


def best_time_window(speed, gap, window_s) -> float:
    """Highest mean speed over window_s consecutive samples, skipping windows that touch a gap."""
    s = pd.Series(np.where(np.asarray(gap, bool), np.nan, np.asarray(speed, float)))
    best = s.rolling(window_s, min_periods=window_s).mean().max()
    return float(best) if pd.notna(best) else NAN


def best_distance(dist_m, gap, distance_m) -> float:
    """Highest mean speed (km/h) over any stretch of at least distance_m, skipping stretches that touch a gap."""
    d = np.asarray(dist_m, float)
    g = np.asarray(gap, bool)
    j = np.searchsorted(d, d + distance_m, side="left")
    i = np.flatnonzero(j < len(d))
    j = j[i]
    gaps = np.concatenate([[0], np.cumsum(g)])
    ok = gaps[j + 1] - gaps[i] == 0
    i, j = i[ok], j[ok]
    if i.size == 0:
        return NAN
    return float(np.max((d[j] - d[i]) / (j - i)) * 3.6)


def best_efforts(seg: pd.DataFrame) -> dict:
    speed, gap, dist = seg["speed_kmh"], seg["gap"], seg["dist_m"]
    return {
        "max_5s_kmh": best_time_window(speed, gap, 5),
        "best_10s_kmh": best_time_window(speed, gap, 10),
        "best_30s_kmh": best_time_window(speed, gap, 30),
        "best_100m_kmh": best_distance(dist, gap, 100),
        "best_500m_kmh": best_distance(dist, gap, 500),
    }


def segment_stats(seg: pd.DataFrame) -> dict:
    dur = len(seg)
    dist = float(seg["step_m"].sum())
    avg = dist / dur * 3.6 if dur else NAN
    return {
        "duration_s": dur,
        "distance_m": dist,
        "avg_speed_kmh": avg,
        "pace_s_per_km": 3600 / avg if avg > 0 else NAN,
        "max_speed_kmh": best_time_window(seg["speed_kmh"], seg["gap"], 5),
        "heading_deg": circ_mean_deg(seg["heading_deg"]),
        "angle_off_deg": float(seg["angle_off_deg"].abs().mean()),
        "vmg_kmh": float(seg["vmg_kmh"].mean()),
        "hr_avg": float(seg["hr"].mean()),
        "hr_max": float(seg["hr"].max()),
    }


def split_stats(track: pd.DataFrame, split_km: float) -> list[dict]:
    idx = (track["dist_m"].to_numpy() // (split_km * 1000)).astype(int)
    starts = np.flatnonzero(np.r_[True, idx[1:] != idx[:-1]])
    ends = np.r_[starts[1:], len(track)]
    return [
        {"split": n + 1, "start_t": int(s), "end_t": int(e), **segment_stats(track.iloc[s:e])}
        for n, (s, e) in enumerate(zip(starts, ends))
    ]


def run_stats(track: pd.DataFrame, runs) -> list[dict]:
    rows = []
    for n, r in enumerate(runs):
        rows.append({
            "run": n + 1,
            "start_t": r.start,
            "end_t": r.end,
            "start_clock": track["time"].iloc[r.start].strftime("%H:%M:%S"),
            "back_up_s": float(r.start - runs[n - 1].end) if n else NAN,
            **segment_stats(track.iloc[r.start:r.end]),
        })
    return rows


def overall_stats(track: pd.DataFrame, runs, run_rows) -> dict:
    total = segment_stats(track)
    mask = np.zeros(len(track), bool)
    for r in runs:
        mask[r.start:r.end] = True
    foil = track[mask]
    t_foil = int(mask.sum())
    avg_foil = float(foil["step_m"].sum()) / t_foil * 3.6 if t_foil else NAN
    longest = max(run_rows, key=lambda row: row["duration_s"]) if run_rows else None
    gaps = [b.start - a.end for a, b in zip(runs, runs[1:])]
    return {
        "start_time": track["time"].iloc[0].isoformat(),
        "duration_s": total["duration_s"],
        "distance_m": total["distance_m"],
        "avg_speed_kmh": total["avg_speed_kmh"],
        "pace_s_per_km": total["pace_s_per_km"],
        **best_efforts(track),
        "hr_avg": total["hr_avg"],
        "hr_max": total["hr_max"],
        "temp_avg": float(track["temp"].mean()),
        "n_runs": len(runs),
        "time_foiling_s": t_foil,
        "pct_foiling": 100 * t_foil / len(track),
        "avg_speed_foiling_kmh": avg_foil,
        "pace_foiling_s_per_km": 3600 / avg_foil if avg_foil > 0 else NAN,
        "vmg_foiling_kmh": float(foil["vmg_kmh"].mean()) if t_foil else NAN,
        "longest_run_s": float(longest["duration_s"]) if longest else NAN,
        "longest_run_m": longest["distance_m"] if longest else NAN,
        "avg_gap_s": float(np.mean(gaps)) if gaps else NAN,
        "max_gap_s": float(max(gaps)) if gaps else NAN,
    }
