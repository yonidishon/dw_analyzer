import numpy as np

from dw_analyzer.runs import Run, detect_runs


def spans(runs):
    return [(r.start, r.end) for r in runs]


def test_short_dip_is_merged():
    speed = [0] * 5 + [20] * 20 + [0] * 2 + [20] * 20 + [0] * 5
    assert spans(detect_runs(speed, 12, 10, 3)) == [(5, 47)]


def test_dip_of_merge_gap_splits():
    speed = [0] * 5 + [20] * 20 + [0] * 3 + [20] * 20
    assert spans(detect_runs(speed, 12, 10, 3)) == [(5, 25), (28, 48)]


def test_short_run_dropped():
    speed = [20] * 9 + [0] * 10 + [20] * 10
    assert spans(detect_runs(speed, 12, 10, 3)) == [(19, 29)]


def test_no_runs():
    assert detect_runs([5] * 100, 12) == []


def test_run_covers_whole_track():
    assert spans(detect_runs([20] * 15, 12)) == [(0, 15)]


def test_threshold_is_strict_and_nan_is_below():
    speed = np.array([12.0] * 20 + [np.nan] * 20 + [12.1] * 20)
    assert spans(detect_runs(speed, 12, 10, 3)) == [(40, 60)]


def test_run_type():
    assert detect_runs([20] * 15, 12) == [Run(0, 15)]
