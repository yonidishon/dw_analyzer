"""Static plotly figures for the PDF report."""
import base64

import numpy as np
import plotly.graph_objects as go

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22"]
GREY = "#9e9e9e"


def _color(i):
    return PALETTE[i % len(PALETTE)]


M_PER_DEG = 111_320.0


def course_bearing(track, downwind_deg) -> float:
    """Compass direction of the track's principal axis, taking the end closer to downwind; in (-180, 180]."""
    xy = track[["x", "y"]].dropna().to_numpy()
    vals, vecs = np.linalg.eigh(np.cov(xy.T))
    east, north = vecs[:, np.argmax(vals)]
    b = np.degrees(np.arctan2(east, north))
    if abs((b - downwind_deg + 180) % 360 - 180) > 90:
        b += 180
    b = (b + 180) % 360 - 180
    return float(180.0 if b == -180 else b)


def _rotated_box(lat, lon, bearing):
    """Track bounding box in the frame of a map rotated by bearing: (lat_mid, lon_mid, v range, u range) in metres."""
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    lat_mid = (np.nanmin(lat) + np.nanmax(lat)) / 2
    lon_mid = (np.nanmin(lon) + np.nanmax(lon)) / 2
    x = (lon - lon_mid) * M_PER_DEG * np.cos(np.radians(lat_mid))
    y = (lat - lat_mid) * M_PER_DEG
    b = np.radians(bearing)
    v = x * np.cos(b) - y * np.sin(b)  # screen right
    u = x * np.sin(b) + y * np.cos(b)  # screen up
    return lat_mid, lon_mid, (np.nanmin(v), np.nanmax(v)), (np.nanmin(u), np.nanmax(u))


def fit_zoom(lat, lon, width_px, height_px, bearing=0.0) -> float:
    lat_mid, _, v, u = _rotated_box(lat, lon, bearing)
    m_per_deg = M_PER_DEG * np.cos(np.radians(lat_mid))
    w_span = max((v[1] - v[0]) / m_per_deg, 1e-3)
    h_span = max((u[1] - u[0]) / m_per_deg, 1e-3)
    z = min(np.log2(360 * width_px / 512 / w_span), np.log2(360 * height_px / 512 / h_span))
    return float(min(z - 0.4, 16))


def fit_center(lat, lon, bearing=0.0) -> dict:
    lat_mid, lon_mid, v, u = _rotated_box(lat, lon, bearing)
    vc, uc = sum(v) / 2, sum(u) / 2
    b = np.radians(bearing)
    x, y = vc * np.cos(b) + uc * np.sin(b), -vc * np.sin(b) + uc * np.cos(b)
    return {"lat": float(lat_mid + y / M_PER_DEG), "lon": float(lon_mid + x / (M_PER_DEG * np.cos(np.radians(lat_mid))))}


def map_figure(track, runs, width, height, bearing=0.0) -> go.Figure:
    fig = go.Figure(go.Scattermap(lat=track["lat"], lon=track["lon"], mode="lines", line=dict(color=GREY, width=2)))
    for i, r in enumerate(runs):
        seg = track.iloc[r.start:r.end]
        fig.add_trace(go.Scattermap(lat=seg["lat"], lon=seg["lon"], mode="lines", line=dict(color=_color(i), width=4)))
    fig.update_layout(
        width=width, height=height, showlegend=False, margin=dict(l=0, r=0, t=0, b=0),
        map=dict(style="carto-voyager", bearing=bearing, center=fit_center(track["lat"], track["lon"], bearing),
                 zoom=fit_zoom(track["lat"], track["lon"], width, height, bearing)),
    )
    return fig


def xy_figure(track, runs, width, height, bearing=0.0) -> go.Figure:
    """Offline fallback: the track in local metres, rotated like the map (screen right, screen up)."""
    b = np.radians(bearing)

    def rot(seg):
        return seg["x"] * np.cos(b) - seg["y"] * np.sin(b), seg["x"] * np.sin(b) + seg["y"] * np.cos(b)

    tx, ty = rot(track)
    fig = go.Figure(go.Scatter(x=tx, y=ty, mode="lines", line=dict(color=GREY, width=2)))
    for i, r in enumerate(runs):
        sx, sy = rot(track.iloc[r.start:r.end])
        fig.add_trace(go.Scatter(x=sx, y=sy, mode="lines", line=dict(color=_color(i), width=4)))
    north_up = bearing == 0
    fig.update_layout(
        width=width, height=height, showlegend=False, margin=dict(l=50, r=10, t=10, b=40),
        xaxis=dict(title="east (m)" if north_up else "m"),
        yaxis=dict(title="north (m)" if north_up else "m", scaleanchor="x"),
    )
    return fig


def timeline_figure(track, runs, threshold_kmh, width, height, tz="UTC") -> go.Figure:
    times = track["time"].dt.tz_convert(tz).dt.tz_localize(None)
    fig = go.Figure(go.Scatter(x=times, y=track["speed_kmh"], name="speed (km/h)", line=dict(color="#1f77b4", width=1)))
    if track["hr"].notna().any():
        fig.add_trace(go.Scatter(x=times, y=track["hr"], name="HR (bpm)", yaxis="y2", line=dict(color="#d62728", width=1)))
    for i, r in enumerate(runs):
        fig.add_vrect(x0=times.iloc[r.start], x1=times.iloc[r.end - 1], fillcolor=_color(i), opacity=0.15, line_width=0)
    fig.add_hline(y=threshold_kmh, line_dash="dash", line_color="#555", line_width=1)
    fig.update_layout(
        width=width, height=height, margin=dict(l=50, r=50, t=10, b=40),
        legend=dict(orientation="h", y=1.12), xaxis=dict(title=f"time ({tz})"), yaxis=dict(title="km/h"),
        yaxis2=dict(title="bpm", overlaying="y", side="right", showgrid=False),
    )
    return fig


def png_data_uri(fig, width, height) -> str:
    png = fig.to_image(format="png", width=width, height=height, scale=2)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
