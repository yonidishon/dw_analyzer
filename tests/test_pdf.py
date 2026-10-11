import pytest

from dw_analyzer.analysis import analyze
from dw_analyzer.prep import prepare
from dw_analyzer.report.figures import (
    angle_figure, corr_figure, course_bearing, fatigue_figure, fit_center, fit_zoom, map_figure, timeline_figure,
    xy_figure, zones_figure,
)
from dw_analyzer.run_analysis import angle_bins, corr_matrix, run_extras, zone_time
from dw_analyzer.report.pdf import pdf_html, render_pdf
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


def test_pdf_zone_cells_coloured(sample_path):
    a = analyze(sample_path, wind_dir=0)
    html = pdf_html(a)
    assert 'class="z4">Z4 (' in html
    for z in range(6):
        assert f".z{z} {{" in html
    assert "Distance / % of session" in html


def test_course_bearing_points_downwind():
    track = prepare(make_raw([5.0] * 300, heading_deg=30.0))
    assert course_bearing(track, 30.0) == pytest.approx(30.0, abs=1)
    assert course_bearing(track, 210.0) == pytest.approx(-150.0, abs=1)
    assert course_bearing(track, 100.0) == pytest.approx(30.0, abs=1)


def test_fit_rotated():
    lat, lon = [32.56, 32.68], [34.90, 34.93]
    assert fit_zoom(lat, lon, 900, 900, bearing=0) == fit_zoom(lat, lon, 900, 900)
    # A north-south course fills a portrait frame better north-up than rotated 90 degrees
    assert fit_zoom([32.5, 32.6], [34.9, 34.9], 400, 1200, bearing=0) > fit_zoom([32.5, 32.6], [34.9, 34.9], 400, 1200, bearing=90) + 1
    c = fit_center(lat, lon)
    assert c["lat"] == pytest.approx(32.62) and c["lon"] == pytest.approx(34.915)
    c90 = fit_center(lat, lon, bearing=90)
    assert c90["lat"] == pytest.approx(32.62) and c90["lon"] == pytest.approx(34.915)


def test_pdf_rotation_caption(sample_path):
    a = analyze(sample_path, wind_dir=0)
    assert f"Map rotated: up = {course_bearing(a.track, a.wind.downwind_deg) % 360:.0f}° (course direction)" in pdf_html(a)


def test_pdf_analysis_figures(sample_path):
    a = analyze(sample_path, wind_dir=0)
    assert [t.name for t in timeline_figure(a.track, a.runs, 12, 1400, 360).data] == ["speed (km/h)", "HR (bpm)", "distance (km)"]
    zones = zones_figure(zone_time(a.track["hr"], a.runs, 188), 188, 500, 400)
    assert [t.type for t in zones.data] == ["bar", "bar"] and "max HR 188" in zones.layout.title.text
    angle = angle_figure(angle_bins(a.track, a.runs), a.wind.downwind_deg, "0° (from --wind-dir)", 600, 520)
    assert angle.data[0].name.startswith("downwind") and angle.layout.title.text.startswith("Best VMG at ")
    rows = [dict(r) for r in a.run_rows]
    run_extras(a.track, a.runs, rows)
    labels, z, n = corr_matrix(rows)
    corr = corr_figure(labels, z, n, 600, 520)
    assert corr.data[0].type == "heatmap" and len(corr.data[0].z) == 12
    fatigue = fatigue_figure(rows, 600, 520)
    assert fatigue.layout.title.text.startswith("Efficiency trend: ")


def test_pdf_layout_like_html(sample_path):
    a = analyze(sample_path, wind_dir=0)
    html = pdf_html(a)
    order = ["<h2>Overall", 'class="card zones"', "<h2>Course and runs", 'id="map"', 'id="right"', "Splits (1 km)",
             "<h2>Speed and heart rate", "<h2>Run analysis"]
    positions = [html.index(m) for m in order]
    assert positions == sorted(positions)
    assert "Splits (2 km)" not in html and "Splits (5 km)" not in html
    analysis = html[html.index("<h2>Run analysis"):]
    assert analysis.count("Runs of 60 s or more") == 3
    assert analysis.count("data:image/png") == 3
    assert html.count("data:image/png") == 6  # zones, map, timeline and the three run analysis plots
