import json

from dw_analyzer.analysis import analyze
from dw_analyzer.report.html import render_html
from helpers import make_raw, write_gpx


def reject_constant(name):
    raise ValueError(f"invalid JSON constant {name}")


def embedded_data(text):
    start = text.index("const DATA = ") + len("const DATA = ")
    end = text.index(";</script>", start)
    return json.loads(text[start:end], parse_constant=reject_constant)


def test_html_report(tmp_path, sample_path):
    a = analyze(sample_path, wind_dir=0)
    out = render_html(a, tmp_path / "r.html")
    text = out.read_text(encoding="utf-8")
    data = embedded_data(text)
    assert len(data["track"]["speed"]) == len(a.track)
    assert set(data["splits"]) == {"1", "2", "5"}
    assert data["params"] == {"threshold_kmh": 12.0, "min_duration_s": 10, "merge_gap_s": 3, "max_hr": 188}
    assert data["meta"]["title"] == "Downwind session 2026-10-08"
    assert "Plotly" in text
    assert "detectRuns" in text
    assert "renderAll" in text
    assert 'id="thr"' in text and 'value="12.0"' in text


def test_html_without_hr(tmp_path):
    gpx = write_gpx(tmp_path / "t.gpx", make_raw([6.0] * 120), extensions=False)
    a = analyze(gpx, wind_dir=0)
    data = embedded_data(render_html(a, tmp_path / "r.html").read_text(encoding="utf-8"))
    assert all(v is None for v in data["track"]["hr"])
    assert data["overall"]["hr_avg"] is None


def test_html_timezone_selector_and_tiles(tmp_path, sample_path):
    from dw_analyzer.report.common import static_text

    a = analyze(sample_path, wind_dir=0)
    text = render_html(a, tmp_path / "r.html").read_text(encoding="utf-8")
    data = embedded_data(text)
    assert data["meta"]["tz"] == "Asia/Jerusalem"
    assert 'id="tz"' in text
    assert 'class="course-runs"' in text
    js = static_text("report.js")
    assert "carto-voyager" in js and "open-street-map" not in js


def test_html_run_analysis_tools(tmp_path):
    gpx = write_gpx(tmp_path / "t.gpx", make_raw([6.0] * 120), extensions=False)
    a = analyze(gpx, wind_dir=90)
    text = render_html(a, tmp_path / "r.html").read_text(encoding="utf-8")
    assert embedded_data(text)["meta"]["downwind_deg"] == a.wind.downwind_deg == 270
    for el in ('id="scatter-x"', 'id="scatter-y"', 'id="polar-r"'):
        assert el in text
    assert "DWA" in text
    overall = text[text.index("<h2>Overall"):text.index("<h2>Course and runs")]
    assert 'id="zones"' in overall
    group = text[text.index('id="course-runs"'):text.index("<h2>Speed and heart rate")]
    positions = [group.index(f'id="{i}"') for i in ["bearing", "map", "runs", "splits"]]
    assert positions == sorted(positions)
    assert "<h2>Splits" not in text
    analysis = text[text.index("<h2>Run analysis"):]
    assert text.index("<h2>Speed and heart rate") < text.index("<h2>Run analysis")
    positions = [analysis.index(f'id="{i}"') for i in ["scatter", "polar", "angle", "corr", "fatigue"]]
    assert positions == sorted(positions)
    assert embedded_data(text)["meta"]["course_bearing_deg"] is not None

def test_html_min_run_input(tmp_path):
    gpx = write_gpx(tmp_path / "t.gpx", make_raw([6.0] * 120))
    text = render_html(analyze(gpx, wind_dir=0), tmp_path / "r.html").read_text(encoding="utf-8")
    assert 'id="min-run"' in text and 'value="60"' in text
    assert text.index('id="min-run"') < text.index('id="max-hr"')


def test_html_max_hr_input_left_of_timezone(tmp_path):
    gpx = write_gpx(tmp_path / "t.gpx", make_raw([6.0] * 120))
    text = render_html(analyze(gpx, wind_dir=0, max_hr=175), tmp_path / "r.html").read_text(encoding="utf-8")
    assert 'id="max-hr"' in text and 'value="175"' in text
    assert text.index('id="max-hr"') < text.index('id="tz"')


def test_html_plots_are_expandable(tmp_path):
    gpx = write_gpx(tmp_path / "t.gpx", make_raw([6.0] * 120))
    text = render_html(analyze(gpx, wind_dir=0), tmp_path / "r.html").read_text(encoding="utf-8")
    body = text[text.index("<body>"):text.index("<script>const DATA")]
    assert body.count("expandable") == 8  # map, zones, timeline and the five run analysis plots
