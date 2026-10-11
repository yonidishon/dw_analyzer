"""Resample a raw GPX track to 1 Hz and derive speed, heading and distance."""
import numpy as np
import pandas as pd

from dw_analyzer.io import GPXError

EARTH_RADIUS_M = 6371008.8
SMOOTH_S = 3
GAP_S = 30


def project(lat, lon, lat0, lon0):
    """Equirectangular projection to metres around (lat0, lon0). Returns (x east, y north)."""
    x = np.radians(np.asarray(lon, dtype=float) - lon0) * EARTH_RADIUS_M * np.cos(np.radians(lat0))
    y = np.radians(np.asarray(lat, dtype=float) - lat0) * EARTH_RADIUS_M
    return x, y


def prepare(raw: pd.DataFrame, smooth_s: int = SMOOTH_S, gap_s: int = GAP_S) -> pd.DataFrame:
    secs = (raw["time"] - raw["time"].iloc[0]).dt.total_seconds().to_numpy()
    if secs[-1] < 1:
        raise GPXError("track is shorter than 1 second")
    grid = np.arange(int(secs[-1]) + 1, dtype=float)

    def interp(values):
        v = np.asarray(values, dtype=float)
        ok = ~np.isnan(v)
        if ok.sum() < 2:
            return np.full(len(grid), np.nan)
        return np.interp(grid, secs[ok], v[ok])

    def smooth(a):
        return pd.Series(a).rolling(smooth_s, center=True, min_periods=1).mean().to_numpy()

    x, y = project(raw["lat"], raw["lon"], raw["lat"].mean(), raw["lon"].mean())
    xs, ys = smooth(interp(x)), smooth(interp(y))

    vx, vy = np.gradient(xs), np.gradient(ys)  # m/s at 1 Hz
    step = np.hypot(np.diff(xs, prepend=xs[0]), np.diff(ys, prepend=ys[0]))

    nxt = np.clip(np.searchsorted(secs, grid, side="right"), 1, len(secs) - 1)
    gap = (secs[nxt] - secs[nxt - 1]) > gap_s

    return pd.DataFrame({
        "t": grid.astype(int),
        "time": raw["time"].iloc[0] + pd.to_timedelta(grid, unit="s"),
        "lat": interp(raw["lat"]),
        "lon": interp(raw["lon"]),
        "x": xs,
        "y": ys,
        "speed_kmh": np.hypot(vx, vy) * 3.6,
        "heading_deg": np.degrees(np.arctan2(vx, vy)) % 360,
        "step_m": step,
        "dist_m": np.cumsum(step),
        "hr": interp(raw["hr"]),
        "temp": interp(raw["temp"]),
        "gap": gap,
    })
