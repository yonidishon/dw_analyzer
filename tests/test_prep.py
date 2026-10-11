import numpy as np
import pytest

from dw_analyzer.io import GPXError, load_gpx
from dw_analyzer.prep import prepare
from helpers import make_raw


def test_constant_speed_track():
    raw = make_raw([5.0] * 30, heading_deg=180.0, dt_s=2.0)  # 60 s at 5 m/s south
    track = prepare(raw)
    assert len(track) == 61
    assert track["t"].tolist() == list(range(61))
    inner = track.iloc[3:-3]
    assert np.allclose(inner["speed_kmh"], 18.0, atol=0.05)
    assert np.allclose(inner["heading_deg"], 180.0, atol=0.5)
    assert track["dist_m"].iloc[-1] == pytest.approx(300.0, abs=6.0)
    assert track["step_m"].iloc[0] == 0.0
    assert np.allclose(track["dist_m"], np.cumsum(track["step_m"]))
    assert not track["gap"].any()
    assert np.allclose(track["hr"], 140.0)


def test_gap_flag():
    raw = make_raw([5.0] * 60)
    raw = raw.drop(index=range(11, 50)).reset_index(drop=True)  # 40 s dropout between t=10 and t=50
    track = prepare(raw)
    assert len(track) == 61
    assert not track["gap"].iloc[5]
    assert track["gap"].iloc[20]
    assert track["gap"].iloc[45]
    assert not track["gap"].iloc[55]


def test_missing_hr_stays_nan():
    raw = make_raw([5.0] * 10, hr=np.nan, temp=np.nan)
    track = prepare(raw)
    assert track["hr"].isna().all()
    assert track["temp"].isna().all()


def test_sub_second_track_rejected():
    raw = make_raw([5.0], dt_s=0.5)
    with pytest.raises(GPXError):
        prepare(raw)


def test_sample(sample_path):
    track = prepare(load_gpx(sample_path))
    assert len(track) == 3432  # 57 min 11 s + 1
    assert 12_000 < track["dist_m"].iloc[-1] < 25_000
    assert track["speed_kmh"].max() < 60
    assert track["time"].iloc[0] == load_gpx(sample_path)["time"].iloc[0]
