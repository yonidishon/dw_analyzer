"""Single-file interactive HTML report."""
import json
import math
from pathlib import Path

import numpy as np
import plotly.offline

from dw_analyzer.report.common import env, run_rule, session_summary, start_label, static_text, title, wind_label


def clean(obj):
    """Make obj strictly JSON-serialisable: NaN/inf -> None, numpy scalars -> Python."""
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [clean(v) for v in obj]
    if isinstance(obj, np.generic):
        obj = obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def _arr(values, digits):
    out = []
    for v in np.asarray(values, dtype=float):
        if not math.isfinite(v):
            out.append(None)
        else:
            out.append(float(v) if digits is None else round(float(v), digits))
    return out


def track_payload(track) -> dict:
    return {
        "t0_ms": int(track["time"].iloc[0].timestamp() * 1000),
        "lat": _arr(track["lat"], 6),
        "lon": _arr(track["lon"], 6),
        "speed": _arr(track["speed_kmh"], None),  # unrounded so JS run boundaries match Python exactly
        "step": _arr(track["step_m"], 3),
        "heading": _arr(track["heading_deg"], 1),
        "vmg": _arr(track["vmg_kmh"], 3),
        "angle_off": _arr(track["angle_off_deg"], 1),
        "hr": _arr(track["hr"], 1),
        "gap": track["gap"].astype(int).tolist(),
    }


def payload(a) -> dict:
    return {
        "meta": {"title": title(a), "wind_label": wind_label(a.wind), "tz": a.tz},
        "params": {"threshold_kmh": a.threshold_kmh, "min_duration_s": a.min_duration_s, "merge_gap_s": a.merge_gap_s},
        "track": track_payload(a.track),
        "overall": clean(a.overall),
        "splits": {str(km): clean(rows) for km, rows in a.splits.items()},
    }


def render_html(a, out_path) -> Path:
    data_json = json.dumps(payload(a), allow_nan=False).replace("</", "<\\/")
    html = env().get_template("report.html.j2").render(
        title=title(a),
        start_label=start_label(a),
        session_summary=session_summary(a),
        run_rule=run_rule(a, with_threshold=False),
        threshold=a.threshold_kmh,
        css=static_text("report.css"),
        plotly_js=plotly.offline.get_plotlyjs(),
        data_json=data_json,
        runs_js=static_text("runs.js"),
        report_js=static_text("report.js"),
    )
    out = Path(out_path)
    out.write_text(html, encoding="utf-8")
    return out
