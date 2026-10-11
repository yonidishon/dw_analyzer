"""Text formatting for report values. Mirrored by the formatters in static/report.js."""
import math

from dw_analyzer.metrics import hr_zone


def _missing(v):
    return v is None or (isinstance(v, (int, float)) and not math.isfinite(v))


def _round(v):
    return int(math.floor(v + 0.5))


def fmt_num(v, digits=1):
    return "-" if _missing(v) else f"{v:.{digits}f}"


def fmt_int(v):
    return "-" if _missing(v) else str(_round(v))


def fmt_kmh(v):
    return "-" if _missing(v) else f"{v:.1f} km/h"


def fmt_duration(s):
    if _missing(s):
        return "-"
    h, rem = divmod(_round(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def fmt_pace(s_per_km):
    if _missing(s_per_km):
        return "-"
    s = _round(s_per_km)
    return f"{s // 60}:{s % 60:02d} /km"


def fmt_distance(m):
    if _missing(m):
        return "-"
    return f"{m / 1000:.2f} km" if m >= 1000 else f"{m:.0f} m"


def fmt_deg(v):
    return "-" if _missing(v) else f"{_round(v)}°"


def fmt_hr_zone(pct):
    return "-" if _missing(pct) else f"Z{hr_zone(pct)} ({math.floor(pct)}%)"


def _distance_share(row):
    return f"{fmt_distance(row['distance_m'])} / {fmt_num(row['distance_pct'], 0)}%"


RUN_COLUMNS = [
    ("#", "run", str),
    ("Start", "start_clock", str),
    ("Duration", "duration_s", fmt_duration),
    ("Distance / % of session", None, _distance_share),
    ("Avg km/h", "avg_speed_kmh", fmt_num),
    ("Pace", "pace_s_per_km", fmt_pace),
    ("Max 5 s", "max_speed_kmh", fmt_num),
    ("Heading", "heading_deg", fmt_deg),
    ("Off downwind", "angle_off_deg", fmt_deg),
    ("VMG km/h", "vmg_kmh", fmt_num),
    ("HR avg", "hr_avg", fmt_int),
    ("HR max", "hr_max", fmt_int),
    ("HR zone", "hr_pct_max", fmt_hr_zone),
    ("Back up", "back_up_s", fmt_duration),
]

SPLIT_COLUMNS = [
    ("#", "split", str),
    ("Distance", "distance_m", fmt_distance),
    ("Duration", "duration_s", fmt_duration),
    ("Avg km/h", "avg_speed_kmh", fmt_num),
    ("Pace", "pace_s_per_km", fmt_pace),
    ("Max 5 s", "max_speed_kmh", fmt_num),
    ("Heading", "heading_deg", fmt_deg),
    ("VMG km/h", "vmg_kmh", fmt_num),
    ("HR avg", "hr_avg", fmt_int),
    ("HR max", "hr_max", fmt_int),
    ("HR zone", "hr_pct_max", fmt_hr_zone),
]


def table_rows(rows, columns):
    """Formatted cells; a column whose key is None formats the whole row."""
    return [[fmt(row) if key is None else fmt(row[key]) for _, key, fmt in columns] for row in rows]


def _speeds(values):
    return "-" if all(_missing(v) for v in values) else " / ".join(fmt_num(v) for v in values) + " km/h"


def _paces(speeds_kmh):
    if all(_missing(v) for v in speeds_kmh):
        return "-"
    return " / ".join("-" if _missing(v) or v <= 0 else fmt_pace(3600 / v).removesuffix(" /km") for v in speeds_kmh) + " /km"


def _speed_pace(speed, pace):
    return "-" if _missing(speed) else f"{fmt_kmh(speed)} · {fmt_pace(pace)}"


def _run(dur, dist, pace):
    return "-" if _missing(dur) else f"{fmt_duration(dur)} · {fmt_distance(dist)} · {fmt_pace(pace)}"


def overall_tiles(o, wind_label):
    """Tile (label, value) pairs; a value may hold a second line after "\n". Mirrored by tiles() in report.js."""
    best_dist = [o["best_100m_kmh"], o["best_500m_kmh"], o["best_1000m_kmh"]]
    return [
        ("Distance", fmt_distance(o["distance_m"])),
        ("Duration", fmt_duration(o["duration_s"])),
        ("Avg speed / pace", _speed_pace(o["avg_speed_kmh"], o["pace_s_per_km"])),
        ("Max speed 5 s / 10 s / 30 s", _speeds([o["max_5s_kmh"], o["best_10s_kmh"], o["best_30s_kmh"]])),
        ("Best 100 m / 500 m / 1000 m", f"{_speeds(best_dist)}\n{_paces(best_dist)}"),
        ("Runs", str(o["n_runs"])),
        ("Time foiling", f"{fmt_duration(o['time_foiling_s'])} ({fmt_num(o['pct_foiling'], 0)}%)"),
        ("Avg speed / pace foiling", _speed_pace(o["avg_speed_foiling_kmh"], o["pace_foiling_s_per_km"])),
        ("VMG foiling", fmt_kmh(o["vmg_foiling_kmh"])),
        ("Best run", _run(o["best_run_s"], o["best_run_m"], o["best_run_pace_s_per_km"])),
        ("Longest run", _run(o["longest_run_s"], o["longest_run_m"], o["longest_run_pace_s_per_km"])),
        ("Avg gap between runs", fmt_duration(o["avg_gap_s"])),
        ("Longest gap", fmt_duration(o["max_gap_s"])),
        ("Heart rate avg / max", "-" if _missing(o["hr_avg"]) else f"{fmt_int(o['hr_avg'])} / {fmt_int(o['hr_max'])} bpm"),
        ("Air temp", "-" if _missing(o["temp_avg"]) else f"{o['temp_avg']:.1f} °C"),
        ("Wind from", wind_label),
    ]
