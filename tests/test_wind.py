import math

import numpy as np
import pandas as pd
import pytest

from dw_analyzer import wind as wind_mod
from dw_analyzer.angles import circ_mean_deg, signed_diff_deg
from dw_analyzer.prep import prepare
from dw_analyzer.wind import Wind, resolve_wind
from helpers import make_raw


def no_fetch(*args, **kwargs):
    return None


def test_circ_mean_wraps():
    r = circ_mean_deg([350, 10])
    assert min(r, 360 - r) < 1e-9
    assert circ_mean_deg([80, 100]) == pytest.approx(90)
    assert math.isnan(circ_mean_deg([]))
    assert circ_mean_deg([90, np.nan]) == pytest.approx(90)


def test_signed_diff():
    assert np.allclose(signed_diff_deg([10, 350, 180], 0), [10, -10, -180])


@pytest.fixture
def south_track():
    return prepare(make_raw([6.0] * 120, heading_deg=180.0))


def test_cli_wins(south_track):
    w = resolve_wind(south_track, 270, 12, fetch=lambda *a: 45.0)
    assert w == Wind(270.0, 90.0, "cli")


def test_open_meteo_used(south_track):
    w = resolve_wind(south_track, None, 12, fetch=lambda *a: 10.0)
    assert w.source == "open-meteo"
    assert w.from_deg == pytest.approx(10.0)
    assert w.downwind_deg == pytest.approx(190.0)


def test_course_fallback(south_track):
    w = resolve_wind(south_track, None, 12, fetch=no_fetch)
    assert w.source == "course"
    assert w.downwind_deg == pytest.approx(180.0, abs=0.5)
    assert min(w.from_deg, 360 - w.from_deg) < 0.5


def test_fetch_open_meteo_parses_response(monkeypatch):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"hourly": {
                "time": ["2026-10-08T11:00", "2026-10-08T12:00", "2026-10-08T13:00", "2026-10-08T14:00", "2026-10-08T20:00"],
                "wind_direction_10m": [100, 350, 10, 0, 180],
            }}

    monkeypatch.setattr(wind_mod.requests, "get", lambda *a, **k: Resp())
    d = wind_mod.fetch_open_meteo(32.6, 34.9, pd.Timestamp("2026-10-08T12:42Z"), pd.Timestamp("2026-10-08T13:40Z"))
    assert min(d, 360 - d) < 1e-6  # mean of 350, 10, 0


def test_fetch_open_meteo_network_error(monkeypatch):
    def boom(*a, **k):
        raise wind_mod.requests.ConnectionError("offline")

    monkeypatch.setattr(wind_mod.requests, "get", boom)
    assert wind_mod.fetch_open_meteo(32.6, 34.9, pd.Timestamp("2026-10-08T12:42Z"), pd.Timestamp("2026-10-08T13:40Z")) is None
