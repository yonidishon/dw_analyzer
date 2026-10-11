# dw_analyzer

Analysis reports for downwind foiling sessions recorded as GPX (for example a Garmin export). One command turns a GPX file into:

- an interactive single-file HTML report, with a run threshold slider that recomputes runs in the browser
- a static PDF report

## Live example

[Interactive example report](https://yonidishon.github.io/dw_analyzer/) (`docs/index.html`, made with `--anonymize`):

```bash
dw-analyze path/to/session.gpx --anonymize --no-pdf --out docs && mv docs/example.html docs/index.html
```

## Install

```bash
uv venv --python 3.12 ~/venvs/dw_analyzer_venv
uv pip install --python ~/venvs/dw_analyzer_venv -e ".[dev]"
```

## Usage

```bash
~/venvs/dw_analyzer_venv/bin/dw-analyze path/to/session.gpx --out out/
```

Writes `out/<gpx name>.html` and `out/<gpx name>.pdf`.

| Flag | Default | Meaning |
|---|---|---|
| `--threshold` | 12 | Run speed threshold in km/h |
| `--min-duration` | 10 | Minimum run length in seconds |
| `--merge-gap` | 3 | Dips below the threshold shorter than this many seconds do not end a run |
| `--wind-dir` | none | Direction the wind comes from, in degrees. If not given, Open-Meteo is queried, and if that fails the mean course direction is used as downwind |
| `--tz` | `Asia/Jerusalem` | IANA time zone for the times shown in the reports (Israel time, including daylight saving) |
| `--max-hr` | 188 | Max heart rate in bpm, used for the HR zone columns |
| `--min-run` | 60 | Shortest run in seconds used by the run analysis plots (PDF, and the starting value of the HTML "Min run" boxes) |
| `--anonymize` | off | For sharing: the session starts 2000-01-01 12:00 (fake date and time), the title has no date or coordinates, and the outputs are named `example.html` / `example.pdf`. The track, heart rate and all metrics are unchanged |
| `--out` | `out` | Output directory |
| `--no-pdf` | off | Only write the HTML report |

## How the track is processed

1. GPX points are resampled to one point per second (Garmin smart recording is irregular).
2. Positions are smoothed with a 3 s rolling mean, then speed, heading and distance are derived.
3. Gaps longer than 30 s between GPS points are interpolated for the map but excluded from best efforts, and they end a run.

## Runs

A run is a period where speed is above the threshold for at least `--min-duration` seconds. Short dips below the threshold (under `--merge-gap` seconds) are merged into the run. In the HTML report the threshold slider re-detects runs and updates the runs table, run statistics, map and timeline. Click a runs table header (#, duration, distance, pace, max 5 s, HR avg, HR max, back up) to sort by it; click again to reverse. The splits table sorts the same way by #, duration, avg km/h, pace, max 5 s, HR avg and HR max. Click a row to show that run or split on the map and timeline (click it again to clear); Ctrl-click (Cmd on macOS) adds or removes rows, also across the two tables; Shift-click selects the range from the last clicked row in the table's current order.

The speed and heart rate graph also shows cumulative distance (km, right-hand axis); hovering the graph shows the values of all lines at that time, with the distance also as a percentage of the whole session.

HTML report layout: the Overall section has the stat tiles with a "Time in HR zones" card on the right. The "Course and runs" card holds the map on the left and the runs and splits tables on the right; the map grows to the same height. Below the speed and heart rate graph, the Run analysis section has five plots (run scatter, run polar, speed by angle off downwind; then correlation matrix, fatigue and efficiency).

The map opens north up. The "Map rotation" slider above the map turns it (-180 to 180°); "Auto" rotates it so the course's main direction points up the screen, downwind up (the principal axis of the GPS track, taking the end closer to downwind), and "North up" resets it; a small arrow in the corner shows north. The PDF map uses the automatic rotation and states it under the map.

Every plot card (map, speed and heart rate, time in HR zones and the run analysis plots) has an enlarge button (⤢) in its top-right corner that opens it in a near full-screen overlay with its controls; close it with the same button (✕), Esc or a click outside.

All plots follow the threshold slider. The five run analysis plots only use runs at least "Min run" seconds long (a box on each of those plots, default 60, 0 = all runs; the boxes stay in sync). It does not affect the map, tables, tiles, speed and heart rate graph or time in HR zones:

- **Run scatter:** each dot is a run. X: pace, duration, distance, or the previous run's duration, distance or HR max. Y: HR avg, HR max, back up time, HR peak after or HR drop 60 s. Shows a least-squares trend line and, in the title, Pearson r with its 95% confidence interval and p-value, Spearman rank correlation and n.
- **Run polar:** north up, clockwise; angle = run mean heading, radius chosen from pace, HR avg, HR max, VMG, distance, duration, HR peak after or HR drop 60 s. A fixed arrow from the centre points downwind; the plot zooms to the sector holding the runs and the downwind direction; the title shows the correlation between the radius and the runs' off downwind angle.
- **Time in HR zones:** share of foiling time and of whole session time in Z0-Z5 (follows Max HR).
- **Correlation matrix:** Pearson r between run #, pace, duration, distance, max 5 s, off downwind, VMG, HR avg, HR max, back up, HR peak after and HR drop 60 s. Click a cell to load that pair into the run scatter (when the pair fits its X and Y choices).
- **Fatigue and efficiency:** pace and HR avg per run # with trend lines; the title gives the efficiency trend (avg km/h per 100 bpm, % change per run).
- **Speed by angle off downwind:** average and best speed of the per-second samples inside runs, in 5° bins of signed angle off downwind (+ = right of downwind), drawn on a compass at each bin's heading with the same downwind arrow as the run polar; the bin with the best average VMG is starred.

HR peak after = highest HR in the 60 s after a run ends (cut at the next run start); HR drop 60 s = that peak minus the HR 60 s later (blank if the next run has started by then).

The PDF follows the same layout as a static snapshot at the CLI threshold, max HR and `--min-run`: page 1 has the tiles and time in HR zones; page 2 the Course and runs card (auto-rotated map beside the runs table and the 1 km splits, with the map as tall as the tables; long tables continue on the next page); then the speed and heart rate graph and three run analysis plots (speed by angle off downwind, correlation matrix, fatigue and efficiency). The run scatter and run polar plots, and the 2 km and 5 km splits, are HTML only.

The runs and splits tables have an HR zone column: the zone of the average HR plus the average as % of max HR (`--max-hr`, also editable in the HTML banner left of the time zone), e.g. `Z4 (83%)`. Zones by % of max HR: Z1 50-60, Z2 60-70, Z3 70-80, Z4 80-90, Z5 90 and up, Z0 below 50; the % is truncated so it always matches the zone. Zone cells are coloured by severity: grey (Z0), blue, green, yellow, orange, red (Z5). The runs table "Distance / % of session" column shows each run's distance and its share of the whole session distance.

## Metrics

All speeds are in km/h. Pace is in min/km.

- **Overall:** distance, duration, average speed and pace, max speed as best 5 s / 10 s / 30 s average, best 100 m / 500 m / 1000 m (speed and pace), number of runs, time and % foiling, average speed and pace while foiling, VMG downwind while foiling, best run (fastest average pace among runs of at least 1 minute: duration, distance, pace), longest run (duration, distance, pace), average and longest gap between runs, heart rate, air temperature, wind direction and its source.
- **Per split (1, 2 or 5 km):** distance, duration, average speed, pace, max speed (5 s), heading, VMG downwind, heart rate.
- **Per run:** start time, duration, distance, average speed, pace, max speed (5 s), heading, angle off downwind, VMG downwind, heart rate, time to get back up since the previous run.

VMG downwind is `speed * cos(heading - downwind direction)`.

## Notes

- Times are shown in the `--tz` time zone. The HTML report also has a time zone selector at the right of the controls banner.
- The HTML report works offline except for the map tiles, which are loaded from CARTO basemaps (OpenStreetMap data). OpenStreetMap's own tile servers refuse requests from local files, so they are not used.
- The PDF map image also needs network access when the report is built. Without it the map background may be blank.

## Tests

```bash
~/venvs/dw_analyzer_venv/bin/pytest
```

The JavaScript parity test needs Node.js and is skipped without it. Tests that use the sample session (`sample_data/activity_24651972498.gpx`, not included in this repo) are skipped when the file is missing.
