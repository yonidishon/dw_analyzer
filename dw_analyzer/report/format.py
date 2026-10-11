"""Text formatting for report values. Mirrored by the formatters in static/report.js."""
import math


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


RUN_COLUMNS = [
    ("#", "run", str),
    ("Start (UTC)", "start_clock", str),
    ("Duration", "duration_s", fmt_duration),
    ("Distance", "distance_m", fmt_distance),
    ("Avg km/h", "avg_speed_kmh", fmt_num),
    ("Pace", "pace_s_per_km", fmt_pace),
    ("Max 5 s", "max_speed_kmh", fmt_num),
    ("Heading", "heading_deg", fmt_deg),
    ("Off downwind", "angle_off_deg", fmt_deg),
    ("VMG km/h", "vmg_kmh", fmt_num),
    ("HR avg", "hr_avg", fmt_int),
    ("HR max", "hr_max", fmt_int),
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
]


def table_rows(rows, columns):
    return [[fmt(row[key]) for _, key, fmt in columns] for row in rows]


def overall_tiles(o, wind_label):
    return [
        ("Distance", fmt_distance(o["distance_m"])),
        ("Duration", fmt_duration(o["duration_s"])),
        ("Avg speed", fmt_kmh(o["avg_speed_kmh"])),
        ("Avg pace", fmt_pace(o["pace_s_per_km"])),
        ("Max speed (5 s)", fmt_kmh(o["max_5s_kmh"])),
        ("Best 10 s", fmt_kmh(o["best_10s_kmh"])),
        ("Best 30 s", fmt_kmh(o["best_30s_kmh"])),
        ("Best 100 m", fmt_kmh(o["best_100m_kmh"])),
        ("Best 500 m", fmt_kmh(o["best_500m_kmh"])),
        ("Runs", str(o["n_runs"])),
        ("Time foiling", f"{fmt_duration(o['time_foiling_s'])} ({fmt_num(o['pct_foiling'], 0)}%)"),
        ("Avg speed foiling", fmt_kmh(o["avg_speed_foiling_kmh"])),
        ("Pace foiling", fmt_pace(o["pace_foiling_s_per_km"])),
        ("VMG foiling", fmt_kmh(o["vmg_foiling_kmh"])),
        ("Longest run", "-" if _missing(o["longest_run_s"])
            else f"{fmt_duration(o['longest_run_s'])} / {fmt_distance(o['longest_run_m'])}"),
        ("Avg gap between runs", fmt_duration(o["avg_gap_s"])),
        ("Longest gap", fmt_duration(o["max_gap_s"])),
        ("Heart rate avg / max", "-" if _missing(o["hr_avg"]) else f"{fmt_int(o['hr_avg'])} / {fmt_int(o['hr_max'])} bpm"),
        ("Air temp", "-" if _missing(o["temp_avg"]) else f"{o['temp_avg']:.1f} °C"),
        ("Wind from", wind_label),
    ]
