import pytest

from dw_analyzer.analysis import analyze
from dw_analyzer.report.figures import fit_zoom, map_figure, xy_figure
from dw_analyzer.report.pdf import render_pdf
from helpers import make_raw, write_gpx


def test_fit_zoom_sample_extent():
    z = fit_zoom([32.56, 32.68], [34.90, 34.93], 900, 900)
    assert 11.5 < z < 13.5


def test_fit_zoom_single_point_is_capped():
    assert fit_zoom([32.6, 32.6], [34.9, 34.9], 900, 900) == 16


def test_figures_have_one_trace_per_run(sample_path):
    a = analyze(sample_path, wind_dir=0)
    assert len(map_figure(a.track, a.runs, 600, 600).data) == 1 + len(a.runs)
    assert len(xy_figure(a.track, a.runs, 600, 600).data) == 1 + len(a.runs)


def test_pdf_report(tmp_path, sample_path):
    a = analyze(sample_path, wind_dir=0)
    out = render_pdf(a, tmp_path / "r.pdf")
    data = out.read_bytes()
    assert data[:4] == b"%PDF"
    assert len(data) > 50_000


def test_pdf_without_runs_or_hr(tmp_path):
    gpx = write_gpx(tmp_path / "t.gpx", make_raw([3.0] * 20), extensions=False)
    a = analyze(gpx, threshold_kmh=99, wind_dir=0)
    assert a.runs == []
    out = render_pdf(a, tmp_path / "r.pdf")
    assert out.read_bytes()[:4] == b"%PDF"


def test_map_uses_carto_tiles(sample_path):
    a = analyze(sample_path, wind_dir=0)
    assert map_figure(a.track, a.runs, 600, 600).layout.map.style == "carto-voyager"
