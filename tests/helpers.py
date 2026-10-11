"""Synthetic tracks for tests."""
import numpy as np
import pandas as pd

R = 6371008.8


def make_raw(speeds_mps, heading_deg=180.0, dt_s=1.0, lat0=32.6, lon0=34.9, hr=140.0, temp=25.0):
    """Raw track shaped like load_gpx output: one point every dt_s, moving at speeds_mps[k] during interval k."""
    speeds = np.asarray(speeds_mps, dtype=float)
    d = np.cumsum(np.concatenate([[0.0], speeds * dt_s]))
    h = np.radians(heading_deg)
    lat = lat0 + np.degrees(d * np.cos(h) / R)
    lon = lon0 + np.degrees(d * np.sin(h) / (R * np.cos(np.radians(lat0))))
    time = pd.Timestamp("2026-10-08T12:00:00Z") + pd.to_timedelta(np.arange(len(d)) * dt_s, unit="s")
    return pd.DataFrame({"time": time, "lat": lat, "lon": lon, "hr": hr, "temp": temp})


def write_gpx(path, raw, extensions=True):
    pts = []
    for r in raw.itertuples():
        ext = ""
        if extensions:
            ext = (
                "<extensions><ns3:TrackPointExtension>"
                f"<ns3:atemp>{r.temp}</ns3:atemp><ns3:hr>{int(r.hr)}</ns3:hr>"
                "</ns3:TrackPointExtension></extensions>"
            )
        pts.append(f'<trkpt lat="{r.lat:.8f}" lon="{r.lon:.8f}"><time>{r.time:%Y-%m-%dT%H:%M:%SZ}</time>{ext}</trkpt>')
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:ns3="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">'
        f"<trk><trkseg>{''.join(pts)}</trkseg></trk></gpx>"
    )
    return path
