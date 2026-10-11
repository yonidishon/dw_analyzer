"""Single-file interactive HTML report."""
import math

import numpy as np


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
