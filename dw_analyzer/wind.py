"""Wind direction: CLI value, Open-Meteo history, or the dominant course direction."""
from dataclasses import dataclass

import pandas as pd
import requests

from dw_analyzer.angles import circ_mean_deg

OPEN_METEO_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"


@dataclass(frozen=True)
class Wind:
    from_deg: float  # direction the wind comes from
    downwind_deg: float  # direction the wind blows towards
    source: str  # "cli" | "open-meteo" | "course"


def _from(from_deg, source) -> Wind:
    return Wind(float(from_deg) % 360, (float(from_deg) + 180) % 360, source)


def fetch_open_meteo(lat, lon, start, end, timeout=5.0):
    """Mean hourly 10 m wind direction (from) over the session, or None if unavailable."""
    try:
        r = requests.get(OPEN_METEO_URL, params={
            "latitude": round(float(lat), 4),
            "longitude": round(float(lon), 4),
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "hourly": "wind_direction_10m",
            "timezone": "UTC",
        }, timeout=timeout)
        r.raise_for_status()
        hourly = r.json()["hourly"]
        times = pd.to_datetime(hourly["time"], utc=True)
        dirs = pd.Series(hourly["wind_direction_10m"], index=times, dtype=float)
        sel = dirs[(times >= start.floor("h")) & (times <= end.ceil("h"))].dropna()
        return circ_mean_deg(sel.to_numpy()) if len(sel) else None
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return None


def course_downwind(track, threshold_kmh) -> float:
    """Mean heading while above the threshold (all samples if never above)."""
    fast = track["speed_kmh"] > threshold_kmh
    return circ_mean_deg(track.loc[fast, "heading_deg"] if fast.any() else track["heading_deg"])


def resolve_wind(track, wind_dir, threshold_kmh, fetch=fetch_open_meteo) -> Wind:
    if wind_dir is not None:
        return _from(wind_dir, "cli")
    d = fetch(track["lat"].mean(), track["lon"].mean(), track["time"].iloc[0], track["time"].iloc[-1])
    if d is not None:
        return _from(d, "open-meteo")
    return _from(course_downwind(track, threshold_kmh) + 180, "course")
