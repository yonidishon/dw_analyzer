"""Circular statistics on compass angles in degrees."""
import numpy as np


def circ_mean_deg(deg) -> float:
    a = np.radians(np.asarray(deg, dtype=float))
    a = a[~np.isnan(a)]
    if a.size == 0:
        return float("nan")
    return float(np.degrees(np.arctan2(np.sin(a).mean(), np.cos(a).mean())) % 360)


def signed_diff_deg(a, b):
    """a - b wrapped to [-180, 180)."""
    return (np.asarray(a, dtype=float) - b + 180) % 360 - 180
