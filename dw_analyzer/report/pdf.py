"""Static PDF snapshot of the analysis."""
from pathlib import Path

from weasyprint import HTML

from dw_analyzer.report.common import env, run_rule, subtitle, title, wind_label
from dw_analyzer.report.figures import (
    PALETTE, angle_figure, corr_figure, course_bearing, fatigue_figure, map_figure, png_data_uri, timeline_figure,
    xy_figure, zones_figure,
)
from dw_analyzer.report.format import RUN_COLUMNS, SPLIT_COLUMNS, overall_tiles, table_rows
from dw_analyzer.run_analysis import angle_bins, corr_matrix, run_extras, zone_time

MAP_RENDER_W = 900  # map image width in px; its height follows the tables beside it
PLOT_W, PLOT_H = 600, 520  # run analysis plot images


def _map_uri(a, bearing, width, height) -> str:
    try:
        return png_data_uri(map_figure(a.track, a.runs, width, height, bearing), width, height)
    except Exception:  # kaleido can fail on map tiles; fall back to a plain track plot
        return png_data_uri(xy_figure(a.track, a.runs, width, height, bearing), width, height)


def _rotation_caption(bearing) -> str:
    return "" if round(bearing) % 360 == 0 else f"Map rotated: up = {bearing % 360:.0f}° (course direction)"


def _find_box(box, element_id):
    element = getattr(box, "element", None)
    if element is not None and element.get("id") == element_id:
        return box
    for child in getattr(box, "children", []):
        found = _find_box(child, element_id)
        if found is not None:
            return found
    return None


def _map_size(html) -> tuple[int, int]:
    """Map image size (px) so its bottom lines up with the runs and splits tables, capped at the page bottom.

    Lays the page out once without the map image and measures the map column and the tables column.
    """
    page = next(p for p in HTML(string=html).render().pages if _find_box(p._page_box, "right") is not None)
    map_box, right = _find_box(page._page_box, "map"), _find_box(page._page_box, "right")
    page_bottom = page._page_box.position_y + page._page_box.margin_height() - page._page_box.margin_bottom
    caption = map_box.height  # the column holds only the caption when there is no image
    height = max(min(right.height, page_bottom - map_box.position_y - 8) - caption, map_box.width * 0.5)
    return MAP_RENDER_W, int(round(MAP_RENDER_W * height / map_box.width))


def _analysis_rows(a):
    """Run rows with the browser-only extras, filtered to runs of at least a.min_run_s (extras use all runs)."""
    rows = [dict(r) for r in a.run_rows]
    run_extras(a.track, a.runs, rows)
    keep = [i for i, r in enumerate(rows) if r["duration_s"] >= a.min_run_s]
    return [rows[i] for i in keep], [a.runs[i] for i in keep]


def pdf_html(a) -> str:
    bearing = course_bearing(a.track, a.wind.downwind_deg)
    rows, runs = _analysis_rows(a)
    labels, z, n = corr_matrix(rows)
    w, h = PLOT_W, PLOT_H
    context = dict(
        title=title(a),
        subtitle=subtitle(a),
        run_rule=run_rule(a),
        tiles=overall_tiles(a.overall, wind_label(a.wind)),
        zones_uri=png_data_uri(zones_figure(zone_time(a.track["hr"], a.runs, a.max_hr), a.max_hr, 520, 420), 520, 420),
        map_uri="",
        map_caption=_rotation_caption(bearing),
        timeline_uri=png_data_uri(timeline_figure(a.track, a.runs, a.threshold_kmh, 1400, 360, a.tz), 1400, 360),
        threshold=f"{a.threshold_kmh:g}",
        run_headers=[c[0] for c in RUN_COLUMNS],
        run_rows=table_rows(a.run_rows, RUN_COLUMNS),
        run_colors=[PALETTE[i % len(PALETTE)] for i in range(len(a.run_rows))],
        split_headers=[c[0] for c in SPLIT_COLUMNS],
        split_rows=table_rows(a.splits[1], SPLIT_COLUMNS),
        min_run=a.min_run_s,
        analysis_uris=[
            png_data_uri(angle_figure(angle_bins(a.track, runs), a.wind.downwind_deg, wind_label(a.wind), w, h), w, h),
            png_data_uri(corr_figure(labels, z, n, w, h), w, h),
            png_data_uri(fatigue_figure(rows, w, h), w, h),
        ],
    )
    template = env().get_template("report_pdf.html.j2")
    map_w, map_h = _map_size(template.render(**context))
    context["map_uri"] = _map_uri(a, bearing, map_w, map_h)
    return template.render(**context)


def render_pdf(a, out_path) -> Path:
    out = Path(out_path)
    HTML(string=pdf_html(a)).write_pdf(out)
    return out
