from dw_analyzer.analysis import SPLITS_KM, analyze


def test_analyze_sample(sample_path):
    a = analyze(sample_path, wind_dir=0)
    assert a.wind.source == "cli"
    assert a.wind.downwind_deg == 180.0
    assert {"vmg_kmh", "angle_off_deg"} <= set(a.track.columns)
    assert set(a.splits) == set(SPLITS_KM)
    assert len(a.splits[1]) >= len(a.splits[2]) >= len(a.splits[5]) >= 1
    assert a.overall["n_runs"] == len(a.runs) == len(a.run_rows)
    assert a.threshold_kmh == 12.0


def test_analyze_course_fallback(sample_path):
    a = analyze(sample_path, fetch_wind=lambda *args: None)
    assert a.wind.source == "course"


def test_threshold_changes_runs(sample_path):
    low = analyze(sample_path, threshold_kmh=6, wind_dir=0)
    high = analyze(sample_path, threshold_kmh=99, wind_dir=0)
    assert high.runs == []
    assert low.overall["time_foiling_s"] > 0
