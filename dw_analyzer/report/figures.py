"""Static plotly figures for the PDF report."""
import base64

import numpy as np
import plotly.graph_objects as go

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22"]
GREY = "#9e9e9e"


def _color(i):
    return PALETTE[i % len(PALETTE)]


def fit_zoom(lat, lon, width_px, height_px) -> float:
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    lat_mid = (np.nanmin(lat) + np.nanmax(lat)) / 2
    lon_span = max(np.nanmax(lon) - np.nanmin(lon), 1e-3)
    lat_span = max((np.nanmax(lat) - np.nanmin(lat)) / np.cos(np.radians(lat_mid)), 1e-3)
    z = min(np.log2(360 * width_px / 512 / lon_span), np.log2(360 * height_px / 512 / lat_span))
    return float(min(z - 0.4, 16))


def map_figure(track, runs, width, height) -> go.Figure:
    fig = go.Figure(go.Scattermap(lat=track["lat"], lon=track["lon"], mode="lines", line=dict(color=GREY, width=2)))
    for i, r in enumerate(runs):
        seg = track.iloc[r.start:r.end]
        fig.add_trace(go.Scattermap(lat=seg["lat"], lon=seg["lon"], mode="lines", line=dict(color=_color(i), width=4)))
    center = dict(lat=(track["lat"].min() + track["lat"].max()) / 2, lon=(track["lon"].min() + track["lon"].max()) / 2)
    fig.update_layout(
        width=width, height=height, showlegend=False, margin=dict(l=0, r=0, t=0, b=0),
        map=dict(style="open-street-map", center=center, zoom=fit_zoom(track["lat"], track["lon"], width, height)),
    )
    return fig


def xy_figure(track, runs, width, height) -> go.Figure:
    fig = go.Figure(go.Scatter(x=track["x"], y=track["y"], mode="lines", line=dict(color=GREY, width=2)))
    for i, r in enumerate(runs):
        seg = track.iloc[r.start:r.end]
        fig.add_trace(go.Scatter(x=seg["x"], y=seg["y"], mode="lines", line=dict(color=_color(i), width=4)))
    fig.update_layout(
        width=width, height=height, showlegend=False, margin=dict(l=50, r=10, t=10, b=40),
        xaxis=dict(title="east (m)"), yaxis=dict(title="north (m)", scaleanchor="x"),
    )
    return fig


def timeline_figure(track, runs, threshold_kmh, width, height) -> go.Figure:
    times = track["time"].dt.tz_convert(None)
    fig = go.Figure(go.Scatter(x=times, y=track["speed_kmh"], name="speed (km/h)", line=dict(color="#1f77b4", width=1)))
    if track["hr"].notna().any():
        fig.add_trace(go.Scatter(x=times, y=track["hr"], name="HR (bpm)", yaxis="y2", line=dict(color="#d62728", width=1)))
    for i, r in enumerate(runs):
        fig.add_vrect(x0=times.iloc[r.start], x1=times.iloc[r.end - 1], fillcolor=_color(i), opacity=0.15, line_width=0)
    fig.add_hline(y=threshold_kmh, line_dash="dash", line_color="#555", line_width=1)
    fig.update_layout(
        width=width, height=height, margin=dict(l=50, r=50, t=10, b=40),
        legend=dict(orientation="h", y=1.12), xaxis=dict(title="time (UTC)"), yaxis=dict(title="km/h"),
        yaxis2=dict(title="bpm", overlaying="y", side="right", showgrid=False),
    )
    return fig


def png_data_uri(fig, width, height) -> str:
    png = fig.to_image(format="png", width=width, height=height, scale=2)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
