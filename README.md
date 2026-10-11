# dw_analyzer

Analysis reports for downwind foiling sessions recorded as GPX (for example a Garmin export). One command turns a GPX file into:

- an interactive single-file HTML report, with a run threshold slider that recomputes runs in the browser
- a static PDF report

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
| `--out` | `out` | Output directory |
| `--no-pdf` | off | Only write the HTML report |

## How the track is processed

1. GPX points are resampled to one point per second (Garmin smart recording is irregular).
2. Positions are smoothed with a 3 s rolling mean, then speed, heading and distance are derived.
3. Gaps longer than 30 s between GPS points are interpolated for the map but excluded from best efforts, and they end a run.

## Runs

A run is a period where speed is above the threshold for at least `--min-duration` seconds. Short dips below the threshold (under `--merge-gap` seconds) are merged into the run. In the HTML report the threshold slider re-detects runs and updates the runs table, run statistics, map and timeline. Click a runs table header (#, duration, distance, pace, max 5 s, HR avg, HR max, back up) to sort by it; click again to reverse.

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
