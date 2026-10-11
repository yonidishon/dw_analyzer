import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from dw_analyzer.analysis import analyze
from dw_analyzer.metrics import run_stats
from dw_analyzer.report.html import clean
from dw_analyzer.run_analysis import CORR_VARS, angle_bins, corr_matrix, lin_fit, pearson, run_extras, zone_time
from dw_analyzer.runs import Run, detect_runs

ANALYSIS_JS = Path(__file__).resolve().parents[1] / "dw_analyzer" / "report" / "static" / "analysis.js"
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

XS = [1, 2, 2, 3, 5, 5, 5, 8, 9, 12]
YS = [3, 1, 4, 4, 2, 9, 7, 8, 8, 10]
RUNS = [Run(10, 60), Run(100, 150), Run(300, 350)]


def test_pearson_matches_numpy():
    assert pearson(XS, YS) == pytest.approx(np.corrcoef(XS, YS)[0, 1], abs=1e-12)


def test_pearson_null_rules():
    assert pearson([1, 2], [3, 4]) is None
    assert pearson([1, 1, 1], [3, 4, 5]) is None


def test_lin_fit():
    slope, intercept = lin_fit([0, 1, 2, 3], [1, 3, 5, 7])
    assert slope == pytest.approx(2) and intercept == pytest.approx(1)
    assert lin_fit([2, 2, 2], [1, 2, 3]) is None
    assert lin_fit([2], [1]) is None


def make_track():
    n = 400
    hr = [100.0 + (i % 7) for i in range(n)]
    hr[60:70] = [110, 120, 130, 140, 150, 170, 160, 150, 140, 130]  # peak 170 at 65
    hr[125] = 160
    hr[150:160] = [120, 122, 124, 126, 128, 190, 130, 130, 130, 130]  # peak 190 at 155
    hr[215] = 99  # HR 60 s after peak at 155
    hr[340:350] = [float("nan")] * 10
    return pd.DataFrame({"hr": hr, "speed_kmh": [10.0] * n})


def make_rows():
    nan = float("nan")
    return [
        {"duration_s": 50, "distance_m": 400.0, "hr_max": 150, "hr_avg": 120.0, "avg_speed_kmh": 12.0},
        {"duration_s": 50, "distance_m": 500.0, "hr_max": 160, "hr_avg": nan, "avg_speed_kmh": 15.0},
        {"duration_s": 50, "distance_m": 600.0, "hr_max": 140, "hr_avg": 150.0, "avg_speed_kmh": 18.0},
    ]


def test_run_extras():
    tr, rows = make_track(), make_rows()
    assert run_extras(tr, RUNS, rows) is None
    r0, r1, r2 = rows
    assert (r0["prev_duration_s"], r0["prev_distance_m"], r0["prev_hr_max"]) == (None, None, None)
    assert (r1["prev_duration_s"], r1["prev_distance_m"], r1["prev_hr_max"]) == (50, 400.0, 150)
    assert (r2["prev_duration_s"], r2["prev_distance_m"], r2["prev_hr_max"]) == (50, 500.0, 160)
    assert r0["hr_peak_after"] == 170 and r0["hr_drop_60s"] is None
    assert r1["hr_peak_after"] == 190 and r1["hr_drop_60s"] == 91
    assert r2["hr_peak_after"] == tr["hr"].iloc[350:400].max() and r2["hr_drop_60s"] is None
    assert r0["efficiency"] == pytest.approx(12 / 120 * 100)
    assert r1["efficiency"] is None
    assert r2["efficiency"] == pytest.approx(12.0)


def test_run_extras_window_cut_and_empty():
    tr = pd.DataFrame({"hr": [100, 101, 102, 150, 140, 130, 120.0]})
    row = {"duration_s": 2, "distance_m": 1, "hr_max": 1, "hr_avg": 100.0, "avg_speed_kmh": 10.0}
    rows = [dict(row)]
    run_extras(tr, [Run(0, 2)], rows)
    assert rows[0]["hr_peak_after"] == 150 and rows[0]["hr_drop_60s"] is None
    rows = [dict(row)]
    run_extras(tr, [Run(0, 7)], rows)
    assert rows[0]["hr_peak_after"] is None and rows[0]["hr_drop_60s"] is None


def angle_track():
    speed = [10.0] * 20 + [20.0] * 20 + [5.0] * 20
    angle = [2.0] * 20 + [-3.0] * 20 + [40.0] * 20
    gap = [False] * 60
    gap[0:5] = [True] * 5
    angle[40:44] = [17.0] * 4  # only 4 samples in bin 17.5 -> dropped
    return pd.DataFrame({"speed_kmh": speed, "angle_off_deg": angle, "gap": gap})


def test_angle_bins():
    bins = angle_bins(angle_track(), [Run(0, 60)])
    assert [b["angle"] for b in bins] == [-2.5, 2.5, 42.5]
    b0, b1, b2 = bins
    assert b1["n"] == 15 and b1["avg"] == 10 and b1["best"] == 10
    assert b0["n"] == 20 and b0["avg"] == 20
    assert b2["n"] == 16 and b2["avg"] == 5
    assert b1["vmg"] == pytest.approx(10 * math.cos(math.radians(2.5)))
    assert b2["vmg"] == pytest.approx(5 * math.cos(math.radians(42.5)))
    assert angle_bins(angle_track(), [Run(20, 40)], 10, 1) == [
        {"angle": -5, "avg": 20, "best": 20, "vmg": pytest.approx(20 * math.cos(math.radians(5))), "n": 20}]


def test_zone_time():
    hr = [90, 120, 140, 160, 170, 180, float("nan"), 100, 100, 100]
    z = zone_time(hr, [Run(1, 7)], 200)
    assert len(z["foiling"]) == 6 and len(z["session"]) == 6
    assert sum(z["foiling"]) == pytest.approx(100) and sum(z["session"]) == pytest.approx(100)
    assert z["foiling"] == pytest.approx([0, 0, 20, 20, 40, 20])
    assert z["session"][0] == pytest.approx(100 / 9) and z["session"][1] == pytest.approx(300 / 9)


def test_zone_time_no_hr():
    assert zone_time([float("nan")] * 5, [Run(0, 3)], 190) == {"foiling": [0] * 6, "session": [0] * 6}
    z = zone_time([100, 100, float("nan")], [Run(2, 3)], 190)
    assert z["foiling"] == [0] * 6 and sum(z["session"]) == pytest.approx(100)
    assert zone_time([100, 100], [Run(0, 2)], 0) == {"foiling": [0] * 6, "session": [0] * 6}


def test_corr_matrix_pairwise_complete():
    nan = float("nan")
    rows = [{"run": i + 1, "pace_s_per_km": 300 - 10 * i, "hr_avg": nan if i == 2 else 120 + 5 * i} for i in range(6)]
    labels, z, n = corr_matrix(rows)
    assert labels == [label for _, label in CORR_VARS] and len(CORR_VARS) == 12
    assert len(z) == 12 and len(z[0]) == 12 and len(n) == 12
    run, pace, hr = 0, 1, 7
    assert z[run][run] == pytest.approx(1) and n[run][run] == 6
    assert z[run][pace] == pytest.approx(-1) and z[pace][run] == pytest.approx(-1)
    assert n[run][hr] == 5 and z[run][hr] is not None
    assert z[run][2] is None and n[run][2] == 0  # Duration absent from all rows


def js(expr, **vars_):
    decls = "".join(f"const {k} = {json.dumps(v)};" for k, v in vars_.items())
    script = (f"const DWA = require({json.dumps(str(ANALYSIS_JS))});{decls}"
              f"process.stdout.write(JSON.stringify({expr}));")
    return json.loads(subprocess.run(["node"], input=script, capture_output=True, text=True, check=True).stdout)


JS_CORR = """(() => {
  const vars = %s, finite = (v) => v !== null && v !== undefined && Number.isFinite(v);
  const z = [], n = [];
  for (const a of vars) { const zr = [], nr = [];
    for (const b of vars) {
      const both = rows.filter((r) => finite(r[a]) && finite(r[b]));
      zr.push(DWA.pearson(both.map((r) => r[a]), both.map((r) => r[b]))); nr.push(both.length);
    }
    z.push(zr); n.push(nr); }
  return {z, n};
})()""" % json.dumps([k for k, _ in CORR_VARS])


def same(a, b, tol=1e-9):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= tol * max(1, abs(a), abs(b))


def dropout_gpx(tmp_path):
    from helpers import make_raw, write_gpx

    raw = make_raw([5.0] * 150 + [40.0] * 60 + [5.0] * 150)
    return write_gpx(tmp_path / "t.gpx", raw.drop(index=range(151, 210)).reset_index(drop=True))


@needs_node
@pytest.mark.parametrize("min_run", [0, 60])
@pytest.mark.parametrize("which", ["sample", "dropout"])
def test_python_matches_js(sample_path, tmp_path, which, min_run):
    a = analyze(sample_path if which == "sample" else dropout_gpx(tmp_path), wind_dir=0)
    track = a.track
    runs = [r for r in detect_runs(track["speed_kmh"].to_numpy(), 12.0, 10, 3, gap=track["gap"].to_numpy())
            if r.end - r.start >= min_run]
    if which == "sample":
        assert runs
    rows = run_stats(track, runs)
    py_rows = [dict(r) for r in rows]
    run_extras(track, runs, py_rows)
    jruns = [{"start": r.start, "end": r.end} for r in runs]
    # JS gets the exact arrays Python uses (unrounded), NaN -> null
    jtrack = {"hr": clean(track["hr"].tolist()), "speed": clean(track["speed_kmh"].tolist()),
              "angle_off": clean(track["angle_off_deg"].tolist()), "gap": track["gap"].astype(int).tolist()}
    jrows = clean(rows)
    out = js("(DWA.runExtras(tr, runs, rows), {rows, bins: DWA.angleBins(tr, runs), zones: DWA.zoneTime(tr.hr, runs, mhr),"
             " corr: %s})" % JS_CORR,
             tr=jtrack, runs=jruns, rows=jrows, mhr=188)
    for p, j in zip(clean(py_rows), out["rows"]):
        for key in ("prev_duration_s", "prev_distance_m", "prev_hr_max", "hr_peak_after", "hr_drop_60s", "efficiency"):
            assert same(p[key], j[key]), (p["run"], key, p[key], j[key])

    bins = angle_bins(track, runs)
    assert [b["angle"] for b in bins] == [b["angle"] for b in out["bins"]]
    for p, j in zip(bins, out["bins"]):
        for key in ("avg", "best", "vmg", "n"):
            assert same(p[key], j[key]), (key, p[key], j[key])

    zones = zone_time(track["hr"].to_numpy(), runs, 188)
    for key in ("foiling", "session"):
        assert all(same(p, j) for p, j in zip(zones[key], out["zones"][key])), key

    _, z, n = corr_matrix(py_rows)
    assert n == out["corr"]["n"]
    assert all(same(p, j, 1e-7) for zr, jr in zip(z, out["corr"]["z"]) for p, j in zip(zr, jr))
