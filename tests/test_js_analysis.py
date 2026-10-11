import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ANALYSIS_JS = Path(__file__).resolve().parents[1] / "dw_analyzer" / "report" / "static" / "analysis.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def js(expr, **vars_):
    """Evaluate a JS expression with DWA loaded and the given JSON variables; return the JSON result."""
    decls = "".join(f"const {k} = {json.dumps(v)};" for k, v in vars_.items())
    script = (f"const DWA = require({json.dumps(str(ANALYSIS_JS))});{decls}"
              f"process.stdout.write(JSON.stringify({expr}));")
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


XS = [1, 2, 2, 3, 5, 5, 5, 8, 9, 12]
YS = [3, 1, 4, 4, 2, 9, 7, 8, 8, 10]


def test_pearson_matches_numpy():
    assert js("DWA.pearson(xs, ys)", xs=XS, ys=YS) == pytest.approx(np.corrcoef(XS, YS)[0, 1], abs=1e-12)


def test_pearson_null_rules():
    assert js("DWA.pearson(xs, ys)", xs=[1, 2], ys=[3, 4]) is None
    assert js("DWA.pearson(xs, ys)", xs=[1, 1, 1], ys=[3, 4, 5]) is None


def test_ranks_average_ties():
    assert js("DWA.ranks(xs)", xs=XS) == list(pd.Series(XS).rank().values)


def test_spearman_matches_pandas():
    expected = pd.Series(XS).rank().corr(pd.Series(YS).rank())
    assert js("DWA.spearman(xs, ys)", xs=XS, ys=YS) == pytest.approx(expected, abs=1e-12)


def test_p_two_sided():
    assert js("DWA.pTwoSided(2.228, 10)") == pytest.approx(0.05, abs=1e-3)
    assert js("DWA.pTwoSided(2.131, 15)") == pytest.approx(0.05, abs=1e-3)
    assert js("DWA.pTwoSided(0, 5)") == 1
    assert js("DWA.pTwoSided(-2.228, 10)") == pytest.approx(0.05, abs=1e-3)


def test_corr_stats_ci_and_p():
    s = js("DWA.corrStats(xs, ys)", xs=XS, ys=YS)
    r = np.corrcoef(XS, YS)[0, 1]
    n = len(XS)
    assert s["n"] == n and s["r"] == pytest.approx(r)
    assert s["lo"] < r < s["hi"]
    se = 1 / math.sqrt(n - 3)
    assert s["lo"] == pytest.approx(math.tanh(math.atanh(r) - 1.959964 * se))
    assert s["hi"] == pytest.approx(math.tanh(math.atanh(r) + 1.959964 * se))
    t = r * math.sqrt((n - 2) / (1 - r * r))
    assert s["p"] == pytest.approx(js("DWA.pTwoSided(t, df)", t=t, df=n - 2))
    assert 0 < s["p"] < 1
    assert s["rho"] == pytest.approx(pd.Series(XS).rank().corr(pd.Series(YS).rank()))


def test_corr_stats_small_n():
    s3 = js("DWA.corrStats(xs, ys)", xs=[1, 2, 3], ys=[1, 3, 2])
    assert s3["n"] == 3 and s3["r"] is not None and s3["p"] is not None
    assert s3["lo"] is None and s3["hi"] is None
    s2 = js("DWA.corrStats(xs, ys)", xs=[1, 2], ys=[1, 3])
    assert s2 == {"n": 2, "r": None, "p": None, "lo": None, "hi": None, "rho": None}


def test_corr_stats_perfect():
    s = js("DWA.corrStats(xs, ys)", xs=[1, 2, 3, 4, 5], ys=[2, 4, 6, 8, 10])
    assert s["r"] == pytest.approx(1) and s["p"] == 0
    assert s["lo"] is None and s["hi"] is None


def test_lin_fit():
    f = js("DWA.linFit(xs, ys)", xs=[0, 1, 2, 3], ys=[1, 3, 5, 7])
    assert f["slope"] == pytest.approx(2) and f["intercept"] == pytest.approx(1)
    assert js("DWA.linFit(xs, ys)", xs=[2, 2, 2], ys=[1, 2, 3]) is None
    assert js("DWA.linFit(xs, ys)", xs=[2], ys=[1]) is None


def make_track():
    n = 400
    hr = [100 + (i % 7) for i in range(n)]
    # run 0: 10-60, run 1: 100-150 (gap of 40 after run 0), run 2: 300-350
    hr[60:70] = [110, 120, 130, 140, 150, 170, 160, 150, 140, 130]  # peak 170 at 65
    hr[125] = 160  # inside run 1, so peak 65 + 60 = 125 is inside the next run
    hr[150:160] = [120, 122, 124, 126, 128, 190, 130, 130, 130, 130]  # peak 190 at 155
    hr[215] = 99  # HR 60 s after peak at 155
    hr[340:350] = [None] * 10
    return {"hr": hr, "speed": [10.0] * n}


RUNS = [{"start": 10, "end": 60}, {"start": 100, "end": 150}, {"start": 300, "end": 350}]


def make_rows():
    return [
        {"duration_s": 50, "distance_m": 400.0, "hr_max": 150, "hr_avg": 120.0, "avg_speed_kmh": 12.0},
        {"duration_s": 50, "distance_m": 500.0, "hr_max": 160, "hr_avg": None, "avg_speed_kmh": 15.0},
        {"duration_s": 50, "distance_m": 600.0, "hr_max": 140, "hr_avg": 150.0, "avg_speed_kmh": 18.0},
    ]


def test_run_extras():
    tr = make_track()
    rows = js("(DWA.runExtras(tr, runs, rows), rows)", tr=tr, runs=RUNS, rows=make_rows())
    r0, r1, r2 = rows
    assert (r0["prev_duration_s"], r0["prev_distance_m"], r0["prev_hr_max"]) == (None, None, None)
    assert (r1["prev_duration_s"], r1["prev_distance_m"], r1["prev_hr_max"]) == (50, 400.0, 150)
    assert (r2["prev_duration_s"], r2["prev_distance_m"], r2["prev_hr_max"]) == (50, 500.0, 160)
    # run 0: window [60, 100) cut by next run start -> peak 170 at 65; 65 + 60 = 125 is inside run 1
    assert r0["hr_peak_after"] == 170 and r0["hr_drop_60s"] is None
    # run 1: window [150, 210) -> peak 190 at 155; hr[215] = 99 and 215 < 300
    assert r1["hr_peak_after"] == 190 and r1["hr_drop_60s"] == 91
    # run 2: window [350, 400) cut by track end; peak + 60 past the end
    assert r2["hr_peak_after"] == max(tr["hr"][350:400]) and r2["hr_drop_60s"] is None
    assert r0["efficiency"] == pytest.approx(12 / 120 * 100)
    assert r1["efficiency"] is None
    assert r2["efficiency"] == pytest.approx(12.0)


def test_run_extras_window_cut_and_empty():
    tr = {"hr": [100, 101, 102, 150, 140, 130, 120], "speed": [10] * 7}
    rows = [{"duration_s": 2, "distance_m": 1, "hr_max": 1, "hr_avg": 100.0, "avg_speed_kmh": 10.0}]
    out = js("(DWA.runExtras(tr, runs, rows), rows)", tr=tr, runs=[{"start": 0, "end": 2}], rows=rows)
    assert out[0]["hr_peak_after"] == 150 and out[0]["hr_drop_60s"] is None
    # run ending at the track end: empty window
    out = js("(DWA.runExtras(tr, runs, rows), rows)", tr=tr, runs=[{"start": 0, "end": 7}], rows=rows)
    assert out[0]["hr_peak_after"] is None and out[0]["hr_drop_60s"] is None


def test_angle_bins():
    n = 60
    speed = [10.0] * 20 + [20.0] * 20 + [5.0] * 20
    angle = [2.0] * 20 + [-3.0] * 20 + [40.0] * 20
    gap = [0] * 60
    gap[0:5] = [1] * 5  # 15 left in bin 2.5
    angle[40:44] = [17.0] * 4  # only 4 samples in bin 17.5 -> dropped
    tr = {"speed": speed, "angle_off": angle, "gap": gap}
    bins = js("DWA.angleBins(tr, runs)", tr=tr, runs=[{"start": 0, "end": 60}])
    assert [b["angle"] for b in bins] == [-2.5, 2.5, 42.5]
    b0, b1, b2 = bins
    assert b1["n"] == 15 and b1["avg"] == 10 and b1["best"] == 10
    assert b0["n"] == 20 and b0["avg"] == 20
    assert b2["n"] == 16 and b2["avg"] == 5
    assert b1["vmg"] == pytest.approx(10 * math.cos(math.radians(2.5)))
    assert b2["vmg"] == pytest.approx(5 * math.cos(math.radians(42.5)))
    # only samples inside the runs count; custom bin size and min samples
    bins = js("DWA.angleBins(tr, runs, 10, 1)", tr=tr, runs=[{"start": 20, "end": 40}])
    assert bins == [{"angle": -5, "avg": 20, "best": 20, "vmg": pytest.approx(20 * math.cos(math.radians(5))), "n": 20}]


def test_zone_time():
    hr = [90, 120, 140, 160, 170, 180, None, 100, 100, 100]
    z = js("DWA.zoneTime(hr, runs, 200)", hr=hr, runs=[{"start": 1, "end": 7}])
    assert len(z["foiling"]) == 6 and len(z["session"]) == 6
    assert sum(z["foiling"]) == pytest.approx(100) and sum(z["session"]) == pytest.approx(100)
    # foiling HR 120,140,160,170,180 -> pct 60,70,80,85,90 -> zones 2,3,4,4,5
    assert z["foiling"] == pytest.approx([0, 0, 20, 20, 40, 20])
    # session adds 90 (45% -> Z0) and three 100 (50% -> Z1)
    assert z["session"][0] == pytest.approx(100 / 9) and z["session"][1] == pytest.approx(300 / 9)


def test_zone_time_no_hr():
    z = js("DWA.zoneTime(hr, runs, 190)", hr=[None] * 5, runs=[{"start": 0, "end": 3}])
    assert z == {"foiling": [0] * 6, "session": [0] * 6}
    z = js("DWA.zoneTime(hr, runs, 190)", hr=[100, 100, None], runs=[{"start": 2, "end": 3}])
    assert z["foiling"] == [0] * 6 and sum(z["session"]) == pytest.approx(100)
