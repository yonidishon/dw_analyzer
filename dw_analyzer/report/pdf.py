"""Static PDF snapshot of the analysis."""
from pathlib import Path

from weasyprint import HTML

from dw_analyzer.analysis import SPLITS_KM
from dw_analyzer.report.common import env, run_rule, subtitle, title, wind_label
from dw_analyzer.report.figures import PALETTE, course_bearing, map_figure, png_data_uri, timeline_figure, xy_figure
from dw_analyzer.report.format import RUN_COLUMNS, SPLIT_COLUMNS, overall_tiles, table_rows

MAP_W, MAP_H = 900, 1300  # portrait: fills the page height beside the runs table


def _map_uri(a, bearing) -> str:
    try:
        return png_data_uri(map_figure(a.track, a.runs, MAP_W, MAP_H, bearing), MAP_W, MAP_H)
    except Exception:  # kaleido can fail on map tiles; fall back to a plain track plot
        return png_data_uri(xy_figure(a.track, a.runs, MAP_W, MAP_H, bearing), MAP_W, MAP_H)


def _rotation_caption(bearing) -> str:
    return "" if round(bearing) % 360 == 0 else f"Map rotated: up = {bearing % 360:.0f}° (course direction)"


def pdf_html(a) -> str:
    bearing = course_bearing(a.track, a.wind.downwind_deg)
    return env().get_template("report_pdf.html.j2").render(
        title=title(a),
        subtitle=subtitle(a),
        run_rule=run_rule(a),
        tiles=overall_tiles(a.overall, wind_label(a.wind)),
        map_uri=_map_uri(a, bearing),
        map_caption=_rotation_caption(bearing),
        timeline_uri=png_data_uri(timeline_figure(a.track, a.runs, a.threshold_kmh, 1400, 360, a.tz), 1400, 360),
        threshold=f"{a.threshold_kmh:g}",
        run_headers=[c[0] for c in RUN_COLUMNS],
        run_rows=table_rows(a.run_rows, RUN_COLUMNS),
        run_colors=[PALETTE[i % len(PALETTE)] for i in range(len(a.run_rows))],
        splits=[(km, [c[0] for c in SPLIT_COLUMNS], table_rows(a.splits[km], SPLIT_COLUMNS)) for km in SPLITS_KM],
    )


def render_pdf(a, out_path) -> Path:
    out = Path(out_path)
    HTML(string=pdf_html(a)).write_pdf(out)
    return out
