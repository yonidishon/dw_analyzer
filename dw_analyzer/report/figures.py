"""Static plotly figures for the PDF report."""
import base64

import numpy as np
import plotly.graph_objects as go

from dw_analyzer.report.format import fmt_deg, fmt_duration, fmt_num
from dw_analyzer.run_analysis import lin_fit, pearson

PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22"]
GREY = "#9e9e9e"
ZONE_BAR_COLORS = ["#90a4ae", "#42a5f5", "#66bb6a", "#ffca28", "#ffa726", "#ef5350"]
TITLE_FONT = dict(size=13)
TICK_STEPS = [5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600]


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
    fig.add_trace(go.Scatter(x=times, y=track["dist_m"] / 1000, name="distance (km)", yaxis="y3",
                             line=dict(color="#2ca02c", width=1)))
    fig.add_hline(y=threshold_kmh, line_dash="dash", line_color="#555", line_width=1)
    fig.update_layout(
        width=width, height=height, margin=dict(l=50, r=50, t=10, b=40),
        legend=dict(orientation="h", y=1.12), xaxis=dict(title=f"time ({tz})", domain=[0, 0.94]), yaxis=dict(title="km/h"),
        yaxis2=dict(title="bpm", overlaying="y", side="right", showgrid=False),
        yaxis3=dict(title="km", overlaying="y", side="right", anchor="free", position=1, showgrid=False),
    )
    return fig


def png_data_uri(fig, width, height) -> str:
    png = fig.to_image(format="png", width=width, height=height, scale=2)
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


# Run analysis plots for the PDF; same content and titles as the HTML (report.js)

def _empty(fig, text):
    fig.add_annotation(text=text, showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def _time_axis(title, values):
    """Axis with m:ss tick labels for values in seconds."""
    axis = dict(title=title)
    if len(values):
        lo, hi = min(values), max(values)
        step = next((t for t in TICK_STEPS if (hi - lo) / t <= 6), 3600)
        ticks = list(np.arange(np.floor(lo / step) * step, hi + step + 1e-9, step))
        axis.update(tickvals=ticks, ticktext=[fmt_duration(v) for v in ticks])
    return axis


def _fixed(v, digits=2):
    return "-" if v is None else f"{v:.{digits}f}"


def polar_sector(angles, pad=10.0):
    """Smallest compass arc holding all angles, padded; as a Plotly sector. Mirrors polarSector() in report.js."""
    a = sorted({float(v) % 360 for v in angles})
    if len(a) < 2:
        return [0, 360]
    gap, start = 360 - a[-1] + a[0], a[0]
    for prev, cur in zip(a, a[1:]):
        if cur - prev > gap:
            gap, start = cur - prev, cur
    span = 360 - gap + 2 * pad
    if span > 330:
        return [0, 360]
    end = start - pad + span  # compass angle h is drawn at screen angle 90 - h
    return [90 - end, 90 - end + span]


def _wind_arrow(downwind_deg, wind_label, lo, hi):
    head = hi - 0.12 * (hi - lo)
    dw = downwind_deg
    return go.Scatterpolar(r=[lo, hi, None, head, hi, head], theta=[dw, dw, None, dw - 5, dw, dw + 5], mode="lines",
                           name=f"downwind (wind from {wind_label})", line=dict(color="#424242", width=3))


def zones_figure(zt, max_hr, width, height) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(width=width, height=height, margin=dict(l=55, r=10, t=45, b=40), barmode="group",
                      title=dict(text=f"Time in HR zones (max HR {max_hr})", font=TITLE_FONT),
                      legend=dict(orientation="h", y=-0.12), yaxis=dict(title="% of time with HR"))
    if not any(zt["session"]):
        return _empty(fig, "No heart rate data")
    labels = [f"Z{i}" for i in range(6)]
    fig.add_trace(go.Bar(name="foiling", x=labels, y=zt["foiling"], marker=dict(color=ZONE_BAR_COLORS)))
    fig.add_trace(go.Bar(name="whole session", x=labels, y=zt["session"],
                         marker=dict(color=ZONE_BAR_COLORS, pattern=dict(shape="/", fgcolor="#424242"))))
    return fig


def angle_figure(bins, downwind_deg, wind_label, width, height) -> go.Figure:
    """Speed per angle-off-downwind bin drawn at its compass heading, with the downwind arrow."""
    fig = go.Figure()
    fig.update_layout(width=width, height=height, margin=dict(l=35, r=35, t=45, b=30), legend=dict(orientation="h", y=-0.05))
    if not bins:
        return _empty(fig, "No samples in runs")
    heading = [(downwind_deg + b["angle"]) % 360 for b in bins]
    best = max(bins, key=lambda b: b["vmg"])
    best_heading = (downwind_deg + best["angle"]) % 360
    hi = max(b["best"] for b in bins) * 1.05
    fig.add_trace(_wind_arrow(downwind_deg, wind_label, 0, hi))
    fig.add_trace(go.Scatterpolar(r=[b["avg"] for b in bins], theta=heading, mode="lines+markers", name="avg speed",
                                  line=dict(color="#1f77b4"), marker=dict(size=4)))
    fig.add_trace(go.Scatterpolar(r=[b["best"] for b in bins], theta=heading, mode="lines+markers", name="best speed",
                                  line=dict(color="#ff7f0e"), marker=dict(size=4)))
    fig.add_trace(go.Scatterpolar(r=[best["avg"]], theta=[best_heading], mode="markers", name="best VMG",
                                  marker=dict(size=12, color="#2ca02c", symbol="star")))
    sign = "+" if best["angle"] > 0 else ""
    fig.update_layout(
        title=dict(text=f"Best VMG at {sign}{best['angle']:g}° (heading {fmt_deg(best_heading)}): {fmt_num(best['vmg'])} km/h",
                   font=TITLE_FONT),
        polar=dict(sector=polar_sector(heading + [downwind_deg], 5),
                   angularaxis=dict(rotation=90, direction="clockwise", dtick=45),
                   radialaxis=dict(title="km/h", range=[0, hi])),
    )
    return fig


def corr_figure(labels, z, n, width, height) -> go.Figure:
    fig = go.Figure(go.Heatmap(x=labels, y=labels, z=z, customdata=n, zmin=-1, zmax=1,
                               colorscale=[[0, "#2166ac"], [0.5, "#f7f7f7"], [1, "#b2182b"]],
                               texttemplate="%{z:.1f}", textfont=dict(size=9), colorbar=dict(thickness=10, len=0.8)))
    fig.update_layout(width=width, height=height, margin=dict(l=95, r=10, t=10, b=95), font=dict(size=10),
                      xaxis=dict(tickangle=-45), yaxis=dict(autorange="reversed"))
    return fig


def fatigue_figure(rows, width, height) -> go.Figure:
    """Pace and HR avg per run # with trend lines; title gives the efficiency trend (% per run)."""
    def pick(key):
        return [r for r in rows if r.get(key) is not None and np.isfinite(r[key])]

    p_rows, h_rows, e_rows = pick("pace_s_per_km"), pick("hr_avg"), pick("efficiency")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[r["run"] for r in p_rows], y=[r["pace_s_per_km"] for r in p_rows], mode="markers",
                             name="pace", marker=dict(size=8, color="#1f77b4")))
    fig.add_trace(go.Scatter(x=[r["run"] for r in h_rows], y=[r["hr_avg"] for r in h_rows], mode="markers",
                             name="HR avg", yaxis="y2", marker=dict(size=8, color="#d62728", symbol="diamond")))
    for sel, key, axis, colour in [(p_rows, "pace_s_per_km", "y", "#1f77b4"), (h_rows, "hr_avg", "y2", "#d62728")]:
        xs, ys = [r["run"] for r in sel], [r[key] for r in sel]
        fit = lin_fit(xs, ys)
        if fit and len(xs) >= 3:
            slope, icpt = fit
            fig.add_trace(go.Scatter(x=[min(xs), max(xs)], y=[icpt + slope * min(xs), icpt + slope * max(xs)], mode="lines",
                                     yaxis=axis, showlegend=False, line=dict(dash="dash", color=colour, width=1.5)))
    ex, ey = [r["run"] for r in e_rows], [r["efficiency"] for r in e_rows]
    fit = lin_fit(ex, ey)
    mean = sum(ey) / len(ey) if ey else None
    pct = 100 * fit[0] / mean if fit and len(ey) >= 3 and mean else None
    eff = "-" if pct is None else f"{'+' if pct >= 0 else ''}{pct:.1f}% per run"
    fig.update_layout(
        width=width, height=height, margin=dict(l=55, r=50, t=50, b=40), legend=dict(orientation="h", y=-0.15),
        title=dict(text=f"Efficiency trend: {eff}<br>r = {_fixed(pearson(ex, ey))} (n = {len(ex)})", font=TITLE_FONT),
        xaxis=dict(title="Run #", dtick=5 if len(rows) > 20 else 1),
        yaxis=_time_axis("Pace (min/km)", [r["pace_s_per_km"] for r in p_rows]),
        yaxis2=dict(title="HR avg (bpm)", overlaying="y", side="right", showgrid=False),
    )
    return fig
