import math

import pytest

from dw_analyzer.analysis import analyze
from dw_analyzer.report.common import run_rule, subtitle, title, wind_label
from dw_analyzer.report.format import (
    RUN_COLUMNS, SPLIT_COLUMNS, fmt_deg, fmt_distance, fmt_duration, fmt_hr_zone, fmt_int, fmt_kmh, fmt_num, fmt_pace,
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
    assert all(isinstance(v, str) for _, v in tiles)
    assert title(a) == "Downwind session 2026-10-08"
    assert subtitle(a).startswith("2026-10-08 15:42 (Asia/Jerusalem)")
    assert "12 km/h" in run_rule(a)


def test_tiles_without_runs(sample_path):
    a = analyze(sample_path, threshold_kmh=99, wind_dir=0)
    tiles = dict(overall_tiles(a.overall, wind_label(a.wind)))
    assert tiles["Runs"] == "0"
    assert tiles["Longest run"] == "-"
    assert tiles["Avg speed / pace foiling"] == "-"
    assert tiles["Best run"] == "-"


def test_combined_tiles(sample_path):
    a = analyze(sample_path, wind_dir=0)
    tiles = dict(overall_tiles(a.overall, wind_label(a.wind)))
    assert list(tiles)[:6] == ["Distance", "Duration", "Avg speed / pace", "Max speed 5 s / 10 s / 30 s",
                               "Best 100 m / 500 m / 1000 m", "Runs"]
    for gone in ["Avg pace", "Best 10 s", "Best 500 m", "Pace foiling"]:
        assert gone not in tiles
    assert tiles["Avg speed / pace"].count(" km/h · ") == 1 and tiles["Avg speed / pace"].endswith(" /km")
    assert tiles["Max speed 5 s / 10 s / 30 s"].count(" / ") == 2
    speeds, paces = tiles["Best 100 m / 500 m / 1000 m"].split("\n")
    assert speeds.endswith("km/h") and speeds.count(" / ") == 2
    assert paces.endswith("/km") and paces.count(" / ") == 2
    assert "Avg speed / pace foiling" in tiles
    assert tiles["Best run"].count(" · ") == 2 and tiles["Best run"].endswith(" /km")
    assert tiles["Longest run"].count(" · ") == 2 and tiles["Longest run"].endswith(" /km")


def test_fmt_hr_zone():
    assert fmt_hr_zone(83.2) == "Z4 (83%)"
    assert fmt_hr_zone(45.0) == "Z0 (45%)"
    assert fmt_hr_zone(79.6) == "Z3 (79%)"  # truncated so the % never contradicts the zone
    assert fmt_hr_zone(float("nan")) == "-"


def test_zone_and_distance_share_columns(sample_path):
    a = analyze(sample_path, wind_dir=0, max_hr=180)
    run_labels = [c[0] for c in RUN_COLUMNS]
    assert run_labels[3] == "Distance / % of session"
    assert run_labels[run_labels.index("HR max") + 1] == "HR zone"
    split_labels = [c[0] for c in SPLIT_COLUMNS]
    assert split_labels[split_labels.index("HR max") + 1] == "HR zone"
    row = table_rows(a.run_rows, RUN_COLUMNS)[0]
    r0 = a.run_rows[0]
    assert row[3] == f"{fmt_distance(r0['distance_m'])} / {r0['distance_pct']:.0f}%"
    assert row[run_labels.index("HR zone")] == fmt_hr_zone(100 * r0["hr_avg"] / 180)
    total = sum(r["distance_pct"] for r in a.run_rows)
    assert total == pytest.approx(100 * sum(r["distance_m"] for r in a.run_rows) / a.overall["distance_m"])
    assert total < 100
