"""Helpers shared by the HTML and PDF reports."""
from importlib.resources import files

from jinja2 import Environment, PackageLoader

from dw_analyzer.report.format import fmt_distance, fmt_duration

WIND_SOURCES = {"cli": "from --wind-dir", "open-meteo": "Open-Meteo", "course": "estimated from course"}


def env() -> Environment:
    return Environment(loader=PackageLoader("dw_analyzer.report", "templates"), autoescape=True)


def static_text(name: str) -> str:
    return (files("dw_analyzer.report") / "static" / name).read_text(encoding="utf-8")


def title(a) -> str:
    return f"Downwind session {a.track['time'].iloc[0]:%Y-%m-%d}"


def subtitle(a) -> str:
    t0 = a.track["time"].iloc[0]
    lat, lon = a.track["lat"].mean(), a.track["lon"].mean()
    return (f"{t0:%Y-%m-%d %H:%M} UTC · {lat:.4f}, {lon:.4f} · "
            f"{fmt_duration(a.overall['duration_s'])} · {fmt_distance(a.overall['distance_m'])}")


def wind_label(wind) -> str:
    return f"{wind.from_deg:.0f}° ({WIND_SOURCES[wind.source]})"


def run_rule(a) -> str:
    return (f"Runs: speed above {a.threshold_kmh:g} km/h for at least {a.min_duration_s} s; "
            f"dips shorter than {a.merge_gap_s} s are merged. Times in UTC.")
