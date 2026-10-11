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
    assert data["params"] == {"threshold_kmh": 12.0, "min_duration_s": 10, "merge_gap_s": 3}
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
