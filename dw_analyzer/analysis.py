"""Run the full analysis of one GPX file."""
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from dw_analyzer.io import load_gpx
from dw_analyzer.metrics import (
    DEFAULT_MAX_HR, add_distance_pct, add_hr_pct, add_vmg, overall_stats, run_stats, split_stats,
)
from dw_analyzer.prep import prepare
from dw_analyzer.runs import MERGE_GAP_S, MIN_DURATION_S, THRESHOLD_KMH, Run, detect_runs
from dw_analyzer.wind import Wind, fetch_open_meteo, resolve_wind

SPLITS_KM = (1, 2, 5)
DEFAULT_TZ = "Asia/Jerusalem"
DEFAULT_MIN_RUN_S = 60  # shortest run used by the run analysis plots


@dataclass
class Analysis:
    source: Path
    track: pd.DataFrame
    wind: Wind
    threshold_kmh: float
    min_duration_s: int
    merge_gap_s: int
    runs: list[Run]
    run_rows: list[dict]
    overall: dict
    splits: dict[int, list[dict]]
    tz: str
    max_hr: int
    min_run_s: int


def analyze(gpx_path, threshold_kmh=THRESHOLD_KMH, min_duration_s=MIN_DURATION_S, merge_gap_s=MERGE_GAP_S,
            wind_dir=None, fetch_wind=fetch_open_meteo, tz=DEFAULT_TZ, max_hr=DEFAULT_MAX_HR,
            min_run_s=DEFAULT_MIN_RUN_S) -> Analysis:
    track = prepare(load_gpx(gpx_path))
    wind = resolve_wind(track, wind_dir, threshold_kmh, fetch=fetch_wind)
    track = add_vmg(track, wind.downwind_deg)
    runs = detect_runs(track["speed_kmh"].to_numpy(), threshold_kmh, min_duration_s, merge_gap_s,
                       gap=track["gap"].to_numpy())
    run_rows = run_stats(track, runs, tz)
    overall = overall_stats(track, runs, run_rows)
    splits = {km: split_stats(track, km) for km in SPLITS_KM}
    add_distance_pct(run_rows, overall["distance_m"])
    for rows in [run_rows, *splits.values()]:
        add_hr_pct(rows, max_hr)
    return Analysis(
        source=Path(gpx_path),
        track=track,
        wind=wind,
        threshold_kmh=float(threshold_kmh),
        min_duration_s=int(min_duration_s),
        merge_gap_s=int(merge_gap_s),
        runs=runs,
        run_rows=run_rows,
        overall=overall,
        splits=splits,
        tz=tz,
        max_hr=int(max_hr),
        min_run_s=int(min_run_s),
    )
