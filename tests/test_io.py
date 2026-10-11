import pytest

from dw_analyzer.io import GPXError, load_gpx
from helpers import make_raw, write_gpx


def test_load_sample(sample_path):
    df = load_gpx(sample_path)
    assert list(df.columns) == ["time", "lat", "lon", "hr", "temp"]
    assert len(df) == 1100
    assert df["time"].is_monotonic_increasing
    assert str(df["time"].dt.tz) == "UTC"
    assert df["hr"].notna().all()
    assert df["temp"].notna().all()


def test_load_without_extensions(tmp_path):
    path = write_gpx(tmp_path / "t.gpx", make_raw([5.0] * 10), extensions=False)
    df = load_gpx(path)
    assert len(df) == 11
    assert df["hr"].isna().all()
    assert df["temp"].isna().all()


def test_sorts_and_drops_duplicate_times(tmp_path):
    path = tmp_path / "t.gpx"
    path.write_text(
        '<?xml version="1.0"?><gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">'
        "<trk><trkseg>"
        '<trkpt lat="32.60" lon="34.90"><time>2026-10-08T12:00:02Z</time></trkpt>'
        '<trkpt lat="32.59" lon="34.90"><time>2026-10-08T12:00:00Z</time></trkpt>'
        '<trkpt lat="32.59" lon="34.90"><time>2026-10-08T12:00:00Z</time></trkpt>'
        '<trkpt lat="32.58" lon="34.90"><time>2026-10-08T12:00:04Z</time></trkpt>'
        "</trkseg></trk></gpx>"
    )
    df = load_gpx(path)
    assert len(df) == 3
    assert df["time"].is_monotonic_increasing
    assert df["lat"].tolist() == [32.59, 32.60, 32.58]


def test_too_few_points(tmp_path):
    path = write_gpx(tmp_path / "t.gpx", make_raw([]))
    with pytest.raises(GPXError, match="at least 2"):
        load_gpx(path)


def test_not_gpx(tmp_path):
    path = tmp_path / "bad.gpx"
    path.write_text("not xml at all")
    with pytest.raises(GPXError):
        load_gpx(path)
