import json
import shutil
import subprocess
from pathlib import Path

import pytest

from dw_analyzer.analysis import analyze
from dw_analyzer.metrics import overall_stats, run_stats
from dw_analyzer.report.html import clean, track_payload
from dw_analyzer.runs import detect_runs

ROOT = Path(__file__).resolve().parents[1]
RUNS_JS = ROOT / "dw_analyzer" / "report" / "static" / "runs.js"
DRIVER = ROOT / "tests" / "js" / "parity.js"
THRESHOLDS = [8.0, 12.0, 15.5, 20.0, 99.0]
ROW_TOL = {"distance_m": 1.0, "avg_speed_kmh": 0.01, "pace_s_per_km": 0.5, "max_speed_kmh": 1e-6,
           "vmg_kmh": 0.01, "angle_off_deg": 0.1, "hr_avg": 0.1, "hr_max": 0.1, "back_up_s": 0}
FOIL_TOL = {"n_runs": 0, "time_foiling_s": 0, "pct_foiling": 1e-9, "avg_speed_foiling_kmh": 0.01,
            "pace_foiling_s_per_km": 0.5, "vmg_foiling_kmh": 0.01, "longest_run_s": 0, "longest_run_m": 1.0,
            "avg_gap_s": 1e-9, "max_gap_s": 0}

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def close(a, b, tol):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol


def test_clean():
    assert clean({"a": float("nan"), "b": [1.5, float("inf")], "c": (2,)}) == {"a": None, "b": [1.5, None], "c": [2]}


def test_js_matches_python(sample_path):
    track = analyze(sample_path, wind_dir=0).track
    payload = {"track": track_payload(track), "thresholds": THRESHOLDS, "min_duration_s": 10, "merge_gap_s": 3}
    res = subprocess.run(["node", str(DRIVER), str(RUNS_JS)], input=json.dumps(payload),
                         capture_output=True, text=True, check=True)
    js = json.loads(res.stdout)
    assert any(out["runs"] for out in js)

    for thr, out in zip(THRESHOLDS, js):
        runs = detect_runs(track["speed_kmh"].to_numpy(), thr, 10, 3)
        assert [(r["start"], r["end"]) for r in out["runs"]] == [(r.start, r.end) for r in runs], thr
        rows = run_stats(track, runs)
        for p, j in zip(clean(rows), out["rows"]):
            assert j["duration_s"] == p["duration_s"]
            for key, tol in ROW_TOL.items():
                assert close(j[key], p[key], tol), (thr, p["run"], key, j[key], p[key])
        o = clean(overall_stats(track, runs, rows))
        for key, tol in FOIL_TOL.items():
            assert close(out["foil"][key], o[key], tol), (thr, key, out["foil"][key], o[key])
