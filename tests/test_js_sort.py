import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from dw_analyzer.metrics import hr_zone

RUNS_JS = Path(__file__).resolve().parents[1] / "dw_analyzer" / "report" / "static" / "runs.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

ROWS = [
    {"run": 1, "duration_s": 60, "pace_s_per_km": 180.0, "hr_avg": 150.0, "back_up_s": None},
    {"run": 2, "duration_s": 300, "pace_s_per_km": 160.0, "hr_avg": None, "back_up_s": 30},
    {"run": 3, "duration_s": 120, "pace_s_per_km": 200.0, "hr_avg": 140.0, "back_up_s": 10},
]


def sort(key, desc):
    script = (f"const DW = require({json.dumps(str(RUNS_JS))});"
              f"const rows = {json.dumps(ROWS)};"
              f"process.stdout.write(JSON.stringify(DW.sortRows(rows, {json.dumps(key)}, {json.dumps(desc)}).map(r => r.run)));"
              f"if (rows[0].run !== 1) throw new Error('input mutated');")
    return json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)


def test_sort_numeric_both_directions():
    assert sort("duration_s", True) == [2, 3, 1]
    assert sort("duration_s", False) == [1, 3, 2]
    assert sort("pace_s_per_km", False) == [2, 1, 3]


def test_missing_values_sort_last():
    assert sort("hr_avg", True) == [1, 3, 2]
    assert sort("hr_avg", False) == [3, 1, 2]
    assert sort("back_up_s", False) == [3, 2, 1]


def js(expr):
    script = f"const DW = require({json.dumps(str(RUNS_JS))}); process.stdout.write(JSON.stringify({expr}));"
    return json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)


def test_pearson_matches_numpy():
    xs, ys = [1, 2, 3, 4, 5.5], [2.0, 1.0, 4.0, 3.5, 7.0]
    assert js(f"DW.pearson({xs}, {ys})") == pytest.approx(float(np.corrcoef(xs, ys)[0, 1]))
    assert js("DW.pearson([1, 2], [3, 4])") is None
    assert js("DW.pearson([1, 2, 3], [5, 5, 5])") is None


def test_hr_zone_matches_python():
    pcts = [10, 49.9, 50, 69.9, 70, 80, 89.99, 90, 105]
    assert js(f"{pcts}.map(DW.hrZone)") == [hr_zone(p) for p in pcts]
    assert js("DW.hrZone(null)") is None
