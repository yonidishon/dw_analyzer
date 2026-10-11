import pytest

from dw_analyzer.cli import main


def test_cli_writes_html_and_pdf(tmp_path, sample_path, capsys):
    assert main([str(sample_path), "--wind-dir", "0", "--out", str(tmp_path)]) == 0
    html = tmp_path / "activity_24651972498.html"
    pdf = tmp_path / "activity_24651972498.pdf"
    assert html.stat().st_size > 1_000_000
    assert pdf.read_bytes()[:4] == b"%PDF"
    assert str(html) in capsys.readouterr().out


def test_cli_no_pdf(tmp_path, sample_path):
    assert main([str(sample_path), "--wind-dir", "0", "--out", str(tmp_path), "--no-pdf", "--threshold", "15"]) == 0
    assert (tmp_path / "activity_24651972498.html").exists()
    assert not (tmp_path / "activity_24651972498.pdf").exists()


def test_cli_bad_file(tmp_path, capsys):
    bad = tmp_path / "bad.gpx"
    bad.write_text("not xml")
    assert main([str(bad), "--out", str(tmp_path)]) == 2
    assert "error:" in capsys.readouterr().err


def test_cli_missing_file(tmp_path, capsys):
    assert main([str(tmp_path / "nope.gpx"), "--out", str(tmp_path)]) == 2
    assert "error:" in capsys.readouterr().err


@pytest.mark.parametrize("flag,value", [("--threshold", "0"), ("--min-duration", "0"), ("--merge-gap", "-1"),
                                        ("--max-hr", "0"), ("--max-hr", "180.5"),
                                        ("--min-run", "-1"), ("--min-run", "1.5")])
def test_cli_rejects_bad_values(tmp_path, sample_path, flag, value):
    with pytest.raises(SystemExit):
        main([str(sample_path), flag, value, "--out", str(tmp_path)])


def test_cli_rejects_unknown_timezone(tmp_path, sample_path):
    with pytest.raises(SystemExit):
        main([str(sample_path), "--tz", "Mars/Olympus", "--out", str(tmp_path)])


def test_cli_timezone_option(tmp_path, sample_path):
    assert main([str(sample_path), "--wind-dir", "0", "--tz", "UTC", "--no-pdf", "--out", str(tmp_path)]) == 0
    assert '"tz": "UTC"' in (tmp_path / "activity_24651972498.html").read_text(encoding="utf-8")


def test_cli_max_hr_option(tmp_path, sample_path):
    assert main([str(sample_path), "--wind-dir", "0", "--max-hr", "180", "--no-pdf", "--out", str(tmp_path)]) == 0
    assert '"max_hr": 180' in (tmp_path / "activity_24651972498.html").read_text(encoding="utf-8")


def test_cli_min_run_option(tmp_path, sample_path):
    assert main([str(sample_path), "--wind-dir", "0", "--min-run", "30", "--no-pdf", "--out", str(tmp_path)]) == 0
    text = (tmp_path / "activity_24651972498.html").read_text(encoding="utf-8")
    assert '"min_run_s": 30' in text
    body = text[text.index("<body>"):text.index("<script>const DATA")]
    assert body.count('class="min-run">Min run <input type="number" min="0" step="1" value="30">') == 5
