"""Helpers shared by the HTML and PDF reports."""
from importlib.resources import files

from jinja2 import Environment, PackageLoader

from dw_analyzer.report.format import fmt_distance, fmt_duration

WIND_SOURCES = {"cli": "from --wind-dir", "open-meteo": "Open-Meteo", "course": "estimated from course"}


def env() -> Environment:
    return Environment(loader=PackageLoader("dw_analyzer.report", "templates"), autoescape=True)


def static_text(name: str) -> str:
    return (files("dw_analyzer.report") / "static" / name).read_text(encoding="utf-8")


def _start(a):
    return a.track["time"].iloc[0].tz_convert(a.tz)


def title(a) -> str:
    return "Downwind session (example)" if a.anonymized else f"Downwind session {_start(a):%Y-%m-%d}"


def start_label(a) -> str:
    return f"{_start(a):%Y-%m-%d %H:%M} ({a.tz})"


def session_summary(a) -> str:
    summary = f"{fmt_duration(a.overall['duration_s'])} · {fmt_distance(a.overall['distance_m'])}"
    if a.anonymized:
        return summary
    lat, lon = a.track["lat"].mean(), a.track["lon"].mean()
    return f"{lat:.4f}, {lon:.4f} · {summary}"


def subtitle(a) -> str:
    return f"{start_label(a)} · {session_summary(a)}"


def wind_label(wind) -> str:
    return f"{wind.from_deg:.0f}° ({WIND_SOURCES[wind.source]})"


def run_rule(a, with_threshold=True) -> str:
    threshold = f"{a.threshold_kmh:g} km/h" if with_threshold else "the threshold"
    times = f"Times in {a.tz}." if with_threshold else "Times in the selected time zone."
    return (f"Runs: speed above {threshold} for at least {a.min_duration_s} s; "
            f"dips shorter than {a.merge_gap_s} s are merged. {times}")
