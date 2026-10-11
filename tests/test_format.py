import math

from dw_analyzer.analysis import analyze
from dw_analyzer.report.common import run_rule, subtitle, title, wind_label
from dw_analyzer.report.format import (
    RUN_COLUMNS, SPLIT_COLUMNS, fmt_deg, fmt_distance, fmt_duration, fmt_int, fmt_kmh, fmt_num, fmt_pace,
    overall_tiles, table_rows,
)
from dw_analyzer.wind import Wind


def test_formatters():
    assert fmt_pace(200) == "3:20 /km"
    assert fmt_pace(float("nan")) == "-"
    assert fmt_duration(3725) == "1:02:05"
    assert fmt_duration(65) == "1:05"
    assert fmt_duration(None) == "-"
    assert fmt_distance(1234.5) == "1.23 km"
    assert fmt_distance(950) == "950 m"
    assert fmt_kmh(21.64) == "21.6 km/h"
    assert fmt_num(math.inf) == "-"
    assert fmt_int(139.6) == "140"
    assert fmt_deg(179.6) == "180°"


def test_wind_label():
    assert wind_label(Wind(270.0, 90.0, "cli")) == "270° (from --wind-dir)"
    assert wind_label(Wind(10.4, 190.4, "course")) == "10° (estimated from course)"


def test_tables_and_tiles(sample_path):
    a = analyze(sample_path, wind_dir=0)
    rows = table_rows(a.run_rows, RUN_COLUMNS)
    assert len(rows) == len(a.run_rows)
    assert all(len(r) == len(RUN_COLUMNS) for r in rows)
    assert table_rows(a.splits[1], SPLIT_COLUMNS)[0][0] == "1"
    tiles = overall_tiles(a.overall, wind_label(a.wind))
    labels = [t[0] for t in tiles]
    assert labels[0] == "Distance"
    assert "Max speed (5 s)" in labels and "Avg pace" in labels and "Pace foiling" in labels
    assert all(isinstance(v, str) for _, v in tiles)
    assert title(a) == "Downwind session 2026-10-08"
    assert subtitle(a).startswith("2026-10-08 12:42 UTC")
    assert "12 km/h" in run_rule(a)


def test_tiles_without_runs(sample_path):
    a = analyze(sample_path, threshold_kmh=99, wind_dir=0)
    tiles = dict(overall_tiles(a.overall, wind_label(a.wind)))
    assert tiles["Runs"] == "0"
    assert tiles["Longest run"] == "-"
    assert tiles["Avg speed foiling"] == "-"
