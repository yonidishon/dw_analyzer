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


def test_dropout_does_not_inflate_best_efforts_or_runs(tmp_path):
    from helpers import make_raw, write_gpx

    # 18 km/h, then a 60 s GPS dropout during which the position jumps 2.4 km, then 18 km/h again
    raw = make_raw([5.0] * 150 + [40.0] * 60 + [5.0] * 150)
    raw = raw.drop(index=range(151, 210)).reset_index(drop=True)
    a = analyze(write_gpx(tmp_path / "t.gpx", raw), wind_dir=0)
    for key in ["max_5s_kmh", "best_10s_kmh", "best_30s_kmh", "best_100m_kmh", "best_500m_kmh"]:
        assert a.overall[key] <= 18.5, key
    assert a.runs
    for r in a.runs:
        assert not a.track["gap"].iloc[r.start:r.end].any()
    assert a.overall["avg_speed_foiling_kmh"] <= 18.5


def test_timezone_default_and_override(sample_path):
    import pandas as pd

    a = analyze(sample_path, wind_dir=0)
    assert a.tz == "Asia/Jerusalem"
    utc = analyze(sample_path, wind_dir=0, tz="UTC")
    first_utc = (pd.Timestamp(utc.overall["start_time"]) + pd.Timedelta(seconds=utc.runs[0].start))
    assert utc.run_rows[0]["start_clock"] == first_utc.strftime("%H:%M:%S")
    assert a.run_rows[0]["start_clock"] == first_utc.tz_convert("Asia/Jerusalem").strftime("%H:%M:%S")


def test_anonymize_shifts_time_after_wind_lookup(sample_path):
    seen = []

    def fetch(lat, lon, start, end):
        seen.append(start)
        return None

    real = analyze(sample_path, wind_dir=0)
    anon = analyze(sample_path, fetch_wind=fetch, anonymize=True)
    assert seen and seen[0].year == 2026  # the weather lookup still uses the real date
    start = anon.track["time"].iloc[0].tz_convert(anon.tz)
    assert (start.year, start.month, start.day, start.hour, start.minute, start.second) == (2000, 1, 1, 12, 0, 0)
    assert anon.anonymized and not real.anonymized
    assert anon.overall["distance_m"] == real.overall["distance_m"]
    assert anon.overall["duration_s"] == real.overall["duration_s"]
    assert [r["duration_s"] for r in anon.run_rows] == [r["duration_s"] for r in real.run_rows]
    assert anon.run_rows[0]["start_clock"].startswith("12:")
