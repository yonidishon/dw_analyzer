"""Detect runs: periods above a speed threshold. Mirrored in report/static/runs.js."""
from dataclasses import dataclass

import numpy as np

THRESHOLD_KMH = 12.0
MIN_DURATION_S = 10
MERGE_GAP_S = 3


@dataclass(frozen=True)
class Run:
    start: int  # first sample, inclusive
    end: int  # last sample + 1


def detect_runs(speed_kmh, threshold_kmh, min_duration_s=MIN_DURATION_S, merge_gap_s=MERGE_GAP_S) -> list[Run]:
    above = np.asarray(speed_kmh, dtype=float) > threshold_kmh
    segments = []
    i, n = 0, len(above)
    while i < n:
        if above[i]:
            j = i
            while j < n and above[j]:
                j += 1
            segments.append([i, j])
            i = j
        else:
            i += 1

    merged = []
    for s, e in segments:
        if merged and s - merged[-1][1] < merge_gap_s:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [Run(s, e) for s, e in merged if e - s >= min_duration_s]
