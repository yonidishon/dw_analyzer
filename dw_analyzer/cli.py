"""Command line entry point: dw-analyze <file.gpx>."""
import argparse
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dw_analyzer.analysis import DEFAULT_MIN_RUN_S, DEFAULT_TZ, analyze
from dw_analyzer.metrics import DEFAULT_MAX_HR
from dw_analyzer.io import GPXError
from dw_analyzer.report.html import render_html
from dw_analyzer.runs import MERGE_GAP_S, MIN_DURATION_S, THRESHOLD_KMH


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dw-analyze", description="Analyse a downwind foiling GPX track.")
    p.add_argument("gpx", type=Path, help="GPX file")
    p.add_argument("--threshold", type=float, default=THRESHOLD_KMH, help="run speed threshold in km/h (default %(default)s)")
    p.add_argument("--min-duration", type=int, default=MIN_DURATION_S, help="minimum run length in seconds (default %(default)s)")
    p.add_argument("--merge-gap", type=int, default=MERGE_GAP_S, help="merge runs separated by fewer seconds than this (default %(default)s)")
    p.add_argument("--wind-dir", type=float, default=None, help="direction the wind comes from, degrees (default: Open-Meteo, then course)")
    p.add_argument("--tz", default=DEFAULT_TZ, help="IANA time zone for displayed times (default %(default)s)")
    p.add_argument("--max-hr", type=int, default=DEFAULT_MAX_HR, help="max heart rate in bpm for HR zones (default %(default)s)")
    p.add_argument("--min-run", type=int, default=DEFAULT_MIN_RUN_S,
                   help="shortest run in seconds used by the run analysis plots (default %(default)s)")
    p.add_argument("--anonymize", action="store_true",
                   help="public example: fake date and time, no coordinates in the title, outputs named example.*")
    p.add_argument("--out", type=Path, default=Path("out"), help="output directory (default %(default)s)")
    p.add_argument("--no-pdf", action="store_true", help="only write the HTML report")
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.threshold <= 0:
        parser.error("--threshold must be positive")
    if args.min_duration < 1:
        parser.error("--min-duration must be at least 1")
    if args.merge_gap < 0:
        parser.error("--merge-gap must not be negative")
    if args.min_run < 0:
        parser.error("--min-run must not be negative")
    if args.max_hr <= 0:
        parser.error("--max-hr must be positive")
    try:
        ZoneInfo(args.tz)
    except (ZoneInfoNotFoundError, ValueError):
        parser.error(f"--tz: unknown time zone {args.tz!r}")

    try:
        a = analyze(args.gpx, args.threshold, args.min_duration, args.merge_gap, args.wind_dir, tz=args.tz,
                    max_hr=args.max_hr, min_run_s=args.min_run, anonymize=args.anonymize)
    except (GPXError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    stem = "example" if args.anonymize else args.gpx.stem  # the GPX name can be a traceable activity ID
    html = render_html(a, args.out / f"{stem}.html")
    print(html)
    if not args.no_pdf:
        from dw_analyzer.report.pdf import render_pdf  # WeasyPrint import is slow; skip it when not needed

        print(render_pdf(a, args.out / f"{stem}.pdf"))
    return 0
