import math

import numpy as np
import pandas as pd
import pytest

from dw_analyzer.metrics import (
    add_distance_pct, add_hr_pct, add_vmg, best_distance, best_efforts, best_time_window, hr_zone, overall_stats,
    run_stats, segment_stats, split_stats,
)
from dw_analyzer.prep import prepare
from dw_analyzer.runs import detect_runs
from helpers import make_raw


def track_from(speeds_mps, heading=180.0, downwind=180.0):
    return add_vmg(prepare(make_raw(speeds_mps, heading_deg=heading)), downwind)


def test_add_vmg():
    t = track_from([5.0] * 60, heading=180.0, downwind=135.0).iloc[5:-5]
    assert np.allclose(t["angle_off_deg"], 45.0, atol=0.5)
    assert np.allclose(t["vmg_kmh"], 18.0 * math.cos(math.radians(45)), atol=0.2)


def test_best_time_window():
    speed = np.array([10.0] * 20 + [30.0] * 5 + [10.0] * 20)
    gap = np.zeros(len(speed), bool)
    assert best_time_window(speed, gap, 5) == pytest.approx(30.0)
    assert best_time_window(speed, gap, 10) == pytest.approx(20.0)


def test_best_time_window_skips_gaps():
    speed = np.array([10.0] * 20 + [30.0] * 5 + [10.0] * 20)
    gap = np.zeros(len(speed), bool)
    gap[22] = True
    assert best_time_window(speed, gap, 5) == pytest.approx(18.0)


def test_best_distance():
    step = np.r_[0, [5.0] * 50, [10.0] * 20, [5.0] * 50]
    d = np.cumsum(step)
    gap = np.zeros(len(d), bool)
    assert best_distance(d, gap, 100) == pytest.approx(36.0)
    assert best_distance(d, gap, 500) == pytest.approx(22.5)


def test_best_distance_skips_gaps():
    step = np.r_[0, [5.0] * 50, [10.0] * 20, [5.0] * 50]
    d = np.cumsum(step)
    gap = np.zeros(len(d), bool)
    gap[51:71] = True
    assert best_distance(d, gap, 100) == pytest.approx(18.0)


def test_best_efforts_short_track():
    t = track_from([5.0] * 3)
    b = best_efforts(t)
    assert math.isnan(b["max_5s_kmh"])  # 4 samples, shorter than 5 s
    assert math.isnan(b["best_10s_kmh"])
    assert math.isnan(b["best_30s_kmh"])
    assert math.isnan(b["best_500m_kmh"])
    assert math.isnan(segment_stats(t.iloc[0:0])["avg_speed_kmh"])


def test_segment_stats_constant_speed():
    t = track_from([5.0] * 120)
    s = segment_stats(t.iloc[10:110])
    assert s["duration_s"] == 100
    assert s["distance_m"] == pytest.approx(500.0, abs=0.5)
    assert s["avg_speed_kmh"] == pytest.approx(18.0, abs=0.05)
    assert s["pace_s_per_km"] == pytest.approx(200.0, abs=1.0)
    assert s["max_speed_kmh"] == pytest.approx(18.0, abs=0.05)
    assert s["heading_deg"] == pytest.approx(180.0, abs=0.5)
    assert s["vmg_kmh"] == pytest.approx(18.0, abs=0.1)
    assert s["hr_avg"] == pytest.approx(140.0)
    assert s["hr_max"] == pytest.approx(140.0)


def test_split_stats():
    t = track_from([5.0] * 600)  # about 3 km
    rows = split_stats(t, 1)
    assert [r["split"] for r in rows] == [1, 2, 3]
    assert rows[0]["start_t"] == 0
    assert rows[-1]["end_t"] == len(t)
    assert rows[0]["distance_m"] == pytest.approx(1000.0, abs=6.0)
    assert rows[1]["duration_s"] == pytest.approx(200, abs=2)
    assert sum(r["duration_s"] for r in rows) == len(t)


def two_run_track():
    return track_from([0.0] * 30 + [6.0] * 60 + [0.0] * 30 + [6.0] * 60 + [0.0] * 30)


def test_run_stats_and_overall():
    t = two_run_track()
    runs = detect_runs(t["speed_kmh"].to_numpy(), 12, 10, 3)
    rows = run_stats(t, runs)
    assert len(rows) == 2
    assert rows[0]["run"] == 1
    assert math.isnan(rows[0]["back_up_s"])
    assert rows[1]["back_up_s"] == pytest.approx(30, abs=3)
    assert rows[0]["avg_speed_kmh"] == pytest.approx(21.6, abs=0.5)
    assert rows[0]["start_clock"] == (pd.Timestamp("2026-10-08T12:00:00Z") + pd.Timedelta(seconds=runs[0].start)).strftime("%H:%M:%S")

    o = overall_stats(t, runs, rows)
    assert o["n_runs"] == 2
    assert o["duration_s"] == len(t)
    assert o["time_foiling_s"] == sum(r.end - r.start for r in runs)
    assert o["pct_foiling"] == pytest.approx(100 * 120 / 211, abs=3)
    assert o["avg_speed_foiling_kmh"] == pytest.approx(21.6, abs=0.5)
    assert o["pace_foiling_s_per_km"] == pytest.approx(3600 / o["avg_speed_foiling_kmh"])
    assert o["longest_run_s"] == max(r["duration_s"] for r in rows)
    assert o["avg_gap_s"] == pytest.approx(rows[1]["back_up_s"])
    assert o["max_5s_kmh"] == pytest.approx(21.6, abs=0.1)
    assert o["temp_avg"] == pytest.approx(25.0)


def test_overall_without_runs():
    t = two_run_track()
    o = overall_stats(t, [], [])
    assert o["n_runs"] == 0
    assert o["time_foiling_s"] == 0
    assert o["pct_foiling"] == 0
    for key in ["avg_speed_foiling_kmh", "pace_foiling_s_per_km", "vmg_foiling_kmh", "longest_run_s", "longest_run_m",
                "longest_run_pace_s_per_km", "best_run_s", "best_run_m", "best_run_pace_s_per_km", "avg_gap_s", "max_gap_s"]:
        assert math.isnan(o[key]), key


def test_best_1000m():
    t = track_from([5.0] * 300)
    assert best_efforts(t)["best_1000m_kmh"] == pytest.approx(18.0, abs=0.05)
    assert math.isnan(best_efforts(track_from([5.0] * 100))["best_1000m_kmh"])


def test_best_run_needs_one_minute_and_longest_run_pace():
    # a 20 s burst at 32 km/h, then a 90 s run at 21.6 km/h, then a 70 s run at 25.2 km/h
    t = track_from([0.0] * 30 + [9.0] * 20 + [0.0] * 30 + [6.0] * 90 + [0.0] * 30 + [7.0] * 70 + [0.0] * 30)
    runs = detect_runs(t["speed_kmh"].to_numpy(), 12, 10, 3)
    rows = run_stats(t, runs)
    assert len(rows) == 3
    o = overall_stats(t, runs, rows)
    best = rows[2]
    assert o["best_run_s"] == best["duration_s"]
    assert o["best_run_m"] == pytest.approx(best["distance_m"])
    assert o["best_run_pace_s_per_km"] == pytest.approx(best["pace_s_per_km"])
    assert o["longest_run_s"] == rows[1]["duration_s"]
    assert o["longest_run_pace_s_per_km"] == pytest.approx(rows[1]["pace_s_per_km"])


def test_no_best_run_when_all_runs_short():
    t = track_from([0.0] * 30 + [9.0] * 40 + [0.0] * 30)
    runs = detect_runs(t["speed_kmh"].to_numpy(), 12, 10, 3)
    o = overall_stats(t, runs, run_stats(t, runs))
    assert o["n_runs"] == 1
    assert math.isnan(o["best_run_s"])
    assert not math.isnan(o["longest_run_pace_s_per_km"])


def test_hr_zone_boundaries():
    assert [hr_zone(p) for p in (10, 49.9, 50, 69.9, 70, 80, 89.99, 90, 105)] == [0, 0, 1, 2, 3, 4, 4, 5, 5]
    assert hr_zone(NAN_) is None


def test_add_hr_pct_and_distance_pct():
    rows = [{"hr_avg": 94.0, "distance_m": 250.0}, {"hr_avg": NAN_, "distance_m": 750.0}]
    add_hr_pct(rows, 188)
    add_distance_pct(rows, 2000.0)
    assert rows[0]["hr_pct_max"] == pytest.approx(50.0)
    assert math.isnan(rows[1]["hr_pct_max"])
    assert [r["distance_pct"] for r in rows] == [12.5, 37.5]


NAN_ = float("nan")
