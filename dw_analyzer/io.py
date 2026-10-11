"""Load GPX track points into a DataFrame."""
import gpxpy
import gpxpy.gpx
import numpy as np
import pandas as pd


class GPXError(ValueError):
    """The GPX file cannot be used for analysis."""


def _extension_values(point):
    hr = temp = np.nan
    for ext in point.extensions:
        for el in ext.iter():
            tag = el.tag.split("}")[-1]
            if tag == "hr" and el.text:
                hr = float(el.text)
            elif tag == "atemp" and el.text:
                temp = float(el.text)
    return hr, temp


def load_gpx(path) -> pd.DataFrame:
    """Return time-sorted track points: time (UTC), lat, lon, hr, temp (NaN when absent)."""
    try:
        with open(path, encoding="utf-8") as f:
            gpx = gpxpy.parse(f)
    except gpxpy.gpx.GPXException as e:
        raise GPXError(f"{path}: not a valid GPX file ({e})") from e

    rows = []
    for track in gpx.tracks:
        for segment in track.segments:
            for p in segment.points:
                if p.time is None:
                    continue
                rows.append((p.time, p.latitude, p.longitude, *_extension_values(p)))

    df = pd.DataFrame(rows, columns=["time", "lat", "lon", "hr", "temp"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time", kind="stable").drop_duplicates("time").reset_index(drop=True)
    if len(df) < 2:
        raise GPXError(f"{path}: need at least 2 timed track points, found {len(df)}")
    return df
