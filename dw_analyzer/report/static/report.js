// Interactive report UI. Requires globals DATA (embedded JSON), DW (runs.js) and Plotly.
(function () {
  "use strict";

  const PALETTE = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#17becf", "#bcbd22"];
  const GREY = "#9e9e9e";
  const HIGHLIGHT = "#ff1744";
  const tr = DATA.track;
  const n = tr.speed.length;
  const color = (i) => PALETTE[i % PALETTE.length];

  // Formatters (mirror dw_analyzer/report/format.py)
  const missing = (v) => v === null || v === undefined || !Number.isFinite(v);
  const num = (v, d = 1) => (missing(v) ? "-" : v.toFixed(d));
  const int = (v) => (missing(v) ? "-" : String(Math.round(v)));
  const kmh = (v) => (missing(v) ? "-" : v.toFixed(1) + " km/h");
  const pad = (x) => String(x).padStart(2, "0");
  const duration = (s) => {
    if (missing(s)) return "-";
    s = Math.round(s);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return h ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
  };
  const pace = (s) => {
    if (missing(s)) return "-";
    s = Math.round(s);
    return `${Math.floor(s / 60)}:${pad(s % 60)} /km`;
  };
  const dist = (m) => (missing(m) ? "-" : m >= 1000 ? (m / 1000).toFixed(2) + " km" : m.toFixed(0) + " m");
  const deg = (v) => (missing(v) ? "-" : Math.round(v) + "°");

  // Local "YYYY-MM-DD HH:MM:SS" per sample in the selected time zone; rebuilt by setTimeZone()
  let times = [];
  let hover = [];
  const clock = (i) => times[i].slice(11, 19);

  function setTimeZone(tz) {
    state.tz = tz;
    const fmt = new Intl.DateTimeFormat("en-CA", {
      timeZone: tz, year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    });
    times = tr.speed.map((_, i) => {
      const p = {};
      for (const part of fmt.formatToParts(new Date(tr.t0_ms + i * 1000))) p[part.type] = part.value;
      return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}:${p.second}`;
    });
    hover = tr.speed.map((v, i) =>
      `${clock(i)}<br>${num(v)} km/h<br>${pace(v > 0 ? 3600 / v : null)}` +
      (missing(tr.hr[i]) ? "" : `<br>HR ${int(tr.hr[i])}`));
    document.getElementById("start-time").textContent = `${times[0].slice(0, 16)} (${tz})`;
  }
  const hasHr = tr.hr.some((v) => !missing(v));

  // Cumulative distance (km) per sample and as % of the session distance
  const cumKm = [];
  tr.step.reduce((acc, v, i) => (cumKm[i] = acc + (missing(v) ? 0 : v)), 0);
  const totalM = cumKm[n - 1];
  const cumPct = cumKm.map((m) => (totalM > 0 ? (100 * m) / totalM : null));
  cumKm.forEach((m, i) => (cumKm[i] = m / 1000));

  const state = { threshold: DATA.params.threshold_kmh, splitKm: "1", mapMode: "speed", tz: DATA.meta.tz, maxHr: DATA.params.max_hr, minRun: 60, bearing: 0, selected: [], anchor: null, runs: [], rows: [], overall: {}, sort: { key: "run", desc: false }, splitSort: { key: "split", desc: false } };

  function compute() {
    state.runs = DW.detectRuns(tr.speed, state.threshold, DATA.params.min_duration_s, DATA.params.merge_gap_s, tr.gap);
    state.rows = DW.runRows(tr, state.runs);
    DWA.runExtras(tr, state.runs, state.rows);
    for (const r of state.rows) r.distance_pct = DATA.overall.distance_m > 0 ? (100 * r.distance_m) / DATA.overall.distance_m : null;
    state.overall = Object.assign({}, DATA.overall, DW.foilStats(tr, state.runs));
    state.selected = [];
    state.anchor = null;
  }

  const speeds = (vs) => (vs.every(missing) ? "-" : vs.map((v) => num(v)).join(" / ") + " km/h");
  const paces = (vs) => (vs.every(missing) ? "-"
    : vs.map((v) => (missing(v) || v <= 0 ? "-" : pace(3600 / v).replace(" /km", ""))).join(" / ") + " /km");
  const speedPace = (v, p) => (missing(v) ? "-" : `${kmh(v)} · ${pace(p)}`);
  const runSummary = (d, m, p) => (missing(d) ? "-" : `${duration(d)} · ${dist(m)} · ${pace(p)}`);

  // Same labels, order and values as overall_tiles() in format.py; "\n" starts a second line
  function tiles(o) {
    const bestDist = [o.best_100m_kmh, o.best_500m_kmh, o.best_1000m_kmh];
    return [
      ["Distance", dist(o.distance_m)],
      ["Duration", duration(o.duration_s)],
      ["Avg speed / pace", speedPace(o.avg_speed_kmh, o.pace_s_per_km)],
      ["Max speed 5 s / 10 s / 30 s", speeds([o.max_5s_kmh, o.best_10s_kmh, o.best_30s_kmh])],
      ["Best 100 m / 500 m / 1000 m", `${speeds(bestDist)}\n${paces(bestDist)}`],
      ["Runs", String(o.n_runs)],
      ["Time foiling", `${duration(o.time_foiling_s)} (${num(o.pct_foiling, 0)}%)`],
      ["Avg speed / pace foiling", speedPace(o.avg_speed_foiling_kmh, o.pace_foiling_s_per_km)],
      ["VMG foiling", kmh(o.vmg_foiling_kmh)],
      ["Best run", runSummary(o.best_run_s, o.best_run_m, o.best_run_pace_s_per_km)],
      ["Longest run", runSummary(o.longest_run_s, o.longest_run_m, o.longest_run_pace_s_per_km)],
      ["Avg gap between runs", duration(o.avg_gap_s)],
      ["Longest gap", duration(o.max_gap_s)],
      ["Heart rate avg / max", missing(o.hr_avg) ? "-" : `${int(o.hr_avg)} / ${int(o.hr_max)} bpm`],
      ["Air temp", missing(o.temp_avg) ? "-" : `${o.temp_avg.toFixed(1)} °C`],
      ["Wind from", DATA.meta.wind_label],
    ];
  }

  // Zone of the average HR plus % of max HR, e.g. "Z4 (83%)" (fmt_hr_zone in format.py)
  const hrZoneText = (hr) => {
    const pct = missing(hr) ? null : (100 * hr) / state.maxHr;
    return missing(pct) ? "-" : `Z${DW.hrZone(pct)} (${Math.floor(pct)}%)`;
  };

  // CSS class .z0-.z5 colours the zone cell by severity
  const zoneClass = (r) => (missing(r.hr_avg) ? "" : `z${DW.hrZone((100 * r.hr_avg) / state.maxHr)}`);

  // Column: [label, formatter, sortKey, descOnFirstClick, cellClass]
  const RUN_COLS = [
    ["#", (r) => String(r.run), "run", false],
    ["Start", (r) => clock(r.start_t)],
    ["Duration", (r) => duration(r.duration_s), "duration_s", true],
    ["Distance / % of session", (r) => `${dist(r.distance_m)} / ${num(r.distance_pct, 0)}%`, "distance_m", true],
    ["Avg km/h", (r) => num(r.avg_speed_kmh)],
    ["Pace", (r) => pace(r.pace_s_per_km), "pace_s_per_km", false],
    ["Max 5 s", (r) => num(r.max_speed_kmh), "max_speed_kmh", true],
    ["Heading", (r) => deg(r.heading_deg)],
    ["Off downwind", (r) => deg(r.angle_off_deg)],
    ["VMG km/h", (r) => num(r.vmg_kmh)],
    ["HR avg", (r) => int(r.hr_avg), "hr_avg", true],
    ["HR max", (r) => int(r.hr_max), "hr_max", true],
    ["HR zone", (r) => hrZoneText(r.hr_avg), null, false, zoneClass],
    ["Back up", (r) => duration(r.back_up_s), "back_up_s", false],
  ];
  const SPLIT_COLS = [
    ["#", (r) => String(r.split), "split", false],
    ["Distance", (r) => dist(r.distance_m)],
    ["Duration", (r) => duration(r.duration_s), "duration_s", true],
    ["Avg km/h", (r) => num(r.avg_speed_kmh), "avg_speed_kmh", true],
    ["Pace", (r) => pace(r.pace_s_per_km), "pace_s_per_km", false],
    ["Max 5 s", (r) => num(r.max_speed_kmh), "max_speed_kmh", true],
    ["Heading", (r) => deg(r.heading_deg)],
    ["VMG km/h", (r) => num(r.vmg_kmh)],
    ["HR avg", (r) => int(r.hr_avg), "hr_avg", true],
    ["HR max", (r) => int(r.hr_max), "hr_max", true],
    ["HR zone", (r) => hrZoneText(r.hr_avg), null, false, zoneClass],
  ];

  // Selected table rows as [start, end] sample ranges; anchor = last clicked row { table, start } for shift ranges
  const isSelected = (s, e) => state.selected.some(([a, b]) => a === s && b === e);

  // Plain click: only this row (again: clear). Ctrl/Cmd-click: toggle this row. Shift-click: range from the anchor
  // in the table's displayed order, replacing the selection.
  function selectRow(ev, table, rows, r) {
    const seg = [r.start_t, r.end_t];
    const anchorIdx = state.anchor && state.anchor.table === table ? rows.findIndex((x) => x.start_t === state.anchor.start) : -1;
    if (ev.shiftKey && anchorIdx >= 0) {
      const i = rows.indexOf(r);
      state.selected = rows.slice(Math.min(i, anchorIdx), Math.max(i, anchorIdx) + 1).map((x) => [x.start_t, x.end_t]);
      return;
    }
    if (ev.ctrlKey || ev.metaKey) {
      state.selected = isSelected(...seg) ? state.selected.filter(([a, b]) => a !== seg[0] || b !== seg[1]) : [...state.selected, seg];
    } else {
      state.selected = state.selected.length === 1 && isSelected(...seg) ? [] : [seg];
    }
    state.anchor = { table, start: r.start_t };
  }

  function renderTiles() {
    document.getElementById("tiles").replaceChildren(...tiles(state.overall).map(([label, value]) => {
      const d = document.createElement("div");
      d.className = "tile";
      const l = document.createElement("span");
      l.className = "label";
      l.textContent = label;
      const v = document.createElement("span");
      v.className = "value";
      v.textContent = value;
      d.append(l, v);
      return d;
    }));
  }

  // sort: {key, desc} of the active column; onSort(next) is called with the new sort on a header click
  function renderTable(el, name, cols, rows, swatch, sort, onSort) {
    const table = document.createElement("table");
    const head = table.createTHead().insertRow();
    for (const [label, , key, firstDesc] of cols) {
      const th = document.createElement("th");
      th.textContent = label;
      if (sort && key) {
        th.className = "sortable";
        if (sort.key === key) th.textContent += sort.desc ? " ▼" : " ▲";
        th.addEventListener("click", () => {
          onSort(sort.key === key ? { key, desc: !sort.desc } : { key, desc: firstDesc });
        });
      }
      head.appendChild(th);
    }
    const body = table.createTBody();
    rows.forEach((r) => {
      const row = body.insertRow();
      cols.forEach(([, f, , , cellClass], c) => {
        const td = row.insertCell();
        td.textContent = f(r);
        if (cellClass) td.className = cellClass(r);
        if (c === 0 && swatch) td.style.borderLeft = `6px solid ${color(r.run - 1)}`;
      });
      if (isSelected(r.start_t, r.end_t)) row.classList.add("selected");
      row.addEventListener("mousedown", (ev) => { if (ev.shiftKey) ev.preventDefault(); }); // no text selection on shift-click
      row.addEventListener("click", (ev) => {
        selectRow(ev, name, rows, r);
        renderAll(false);
      });
    });
    el.replaceChildren(table);
  }

  function renderSplits() {
    const s = state.splitSort;
    renderTable(document.getElementById("splits"), "splits", SPLIT_COLS, DW.sortRows(DATA.splits[state.splitKm], s.key, s.desc), false, s, (next) => {
      state.splitSort = next;
      renderSplits();
    });
  }

  function renderRuns() {
    const el = document.getElementById("runs");
    if (state.rows.length) {
      renderTable(el, "runs", RUN_COLS, DW.sortRows(state.rows, state.sort.key, state.sort.desc), true, state.sort, (s) => {
        state.sort = s;
        renderRuns();
      });
    } else {
      const p = document.createElement("p");
      p.className = "empty";
      p.textContent = `No runs above ${state.threshold} km/h`;
      el.replaceChildren(p);
    }
  }

  // Map
  const mapEl = document.getElementById("map");
  const lats = tr.lat.filter((v) => !missing(v));
  const lons = tr.lon.filter((v) => !missing(v));
  const M_PER_DEG = 111320;
  const latMid = (Math.min(...lats) + Math.max(...lats)) / 2;
  const lonMid = (Math.min(...lons) + Math.max(...lons)) / 2;
  const cosLat = Math.cos((latMid * Math.PI) / 180);
  const xs = lons.map((v) => (v - lonMid) * M_PER_DEG * cosLat);
  const ys = lats.map((v) => (v - latMid) * M_PER_DEG);

  // Track bounding box in the frame of a map rotated by bearing (metres; v = screen right, u = screen up), as rotated_box() in figures.py
  function rotatedBox(bearing) {
    const b = (bearing * Math.PI) / 180, c = Math.cos(b), s = Math.sin(b);
    const v = xs.map((x, i) => x * c - ys[i] * s), u = xs.map((x, i) => x * s + ys[i] * c);
    return { v: [Math.min(...v), Math.max(...v)], u: [Math.min(...u), Math.max(...u)], c, s };
  }

  // Same formulas as fit_zoom() and fit_center() in figures.py
  function fitZoom(w, h, bearing) {
    const { v, u } = rotatedBox(bearing);
    const wSpan = Math.max((v[1] - v[0]) / (M_PER_DEG * cosLat), 1e-3);
    const hSpan = Math.max((u[1] - u[0]) / (M_PER_DEG * cosLat), 1e-3);
    const z = Math.min(Math.log2((360 * w) / 512 / wSpan), Math.log2((360 * h) / 512 / hSpan));
    return Math.min(z - 0.4, 16);
  }

  function fitCenter(bearing) {
    const { v, u, c, s } = rotatedBox(bearing);
    const vc = (v[0] + v[1]) / 2, uc = (u[0] + u[1]) / 2;
    const x = vc * c + uc * s, y = -vc * s + uc * c;
    return { lat: latMid + y / M_PER_DEG, lon: lonMid + x / (M_PER_DEG * cosLat) };
  }

  function line(s, e, lineColor, width, name, withHover) {
    return {
      type: "scattermap", mode: "lines", name,
      lat: tr.lat.slice(s, e), lon: tr.lon.slice(s, e),
      line: { color: lineColor, width },
      text: hover.slice(s, e), hoverinfo: withHover ? "text" : "skip",
    };
  }

  function mapTraces() {
    const traces = [];
    if (state.mapMode === "speed") {
      traces.push({
        type: "scattermap", mode: "markers", name: "speed", lat: tr.lat, lon: tr.lon,
        marker: { size: 5, color: tr.speed, colorscale: "Viridis", colorbar: { title: { text: "km/h" } } },
        text: hover, hoverinfo: "text",
      });
    } else {
      traces.push(line(0, n, GREY, 2, "not foiling", true));
      state.runs.forEach((r, i) => traces.push(line(r.start, r.end, color(i), 4, `Run ${i + 1}`, true)));
    }
    const sp = DATA.splits[state.splitKm];
    traces.push({
      type: "scattermap", mode: "markers", name: "split starts",
      lat: sp.map((r) => tr.lat[r.start_t]), lon: sp.map((r) => tr.lon[r.start_t]),
      marker: { size: 9, color: "#212121" },
      text: sp.map((r) => `Split ${r.split} start (${state.splitKm} km splits)`), hoverinfo: "text",
    });
    traces.push({
      type: "scattermap", mode: "markers", name: "run starts",
      lat: state.runs.map((r) => tr.lat[r.start]), lon: state.runs.map((r) => tr.lon[r.start]),
      marker: { size: 12, color: state.runs.map((_, i) => color(i)) },
      text: state.runs.map((r, i) => `Run ${i + 1} start ${clock(r.start)}`), hoverinfo: "text",
    });
    for (const [s, e] of state.selected) traces.push(line(s, e, HIGHLIGHT, 7, "selected", false));
    return traces;
  }

  // Side by side, the map column is as tall as the right column (runs and splits); stacked, the map has a fixed height
  const MAP_H = 560;
  const courseRuns = document.getElementById("course-runs");
  const leftCol = document.getElementById("left");
  const rightCol = document.getElementById("right");
  const stacked = () => getComputedStyle(courseRuns).gridTemplateColumns.trim().split(/\s+/).length === 1;
  const MAP_MIN_H = 300;
  const mapHeight = () => heightFor("map", stacked() ? MAP_H : Math.max(rightCol.offsetHeight - (leftCol.offsetHeight - mapEl.offsetHeight), MAP_MIN_H));

  function syncMapHeight() {
    const h = mapHeight();
    if (mapEl.offsetHeight !== h && mapEl.data) Plotly.relayout(mapEl, { height: h });
  }

  function renderMap() {
    const h = mapHeight();
    const w = mapEl.clientWidth || 800;
    // uirevision follows the bearing so a new rotation re-fits the view, while pan/zoom survive other updates
    Plotly.react(mapEl, mapTraces(), {
      width: w, height: h, margin: { l: 0, r: 0, t: 0, b: 0 }, showlegend: false, uirevision: `map ${state.bearing} ${expanded ? "enlarged" : ""}`,
      map: { style: "carto-voyager", bearing: state.bearing, center: fitCenter(state.bearing), zoom: fitZoom(w, h, state.bearing) },
    });
    showBearing(state.bearing);
  }

  const bearingInput = document.getElementById("bearing");
  const autoBearing = Math.round(DATA.meta.course_bearing_deg);

  function showBearing(b) {
    bearingInput.value = b;
    document.getElementById("bearing-val").textContent = b;
    document.getElementById("north").style.transform = `rotate(${-b}deg)`;
  }

  function setBearing(b) {
    state.bearing = b;
    renderMap();
  }

  // Timeline
  const tlEl = document.getElementById("timeline");

  function renderTimeline() {
    const traces = [{ type: "scatter", mode: "lines", x: times, y: tr.speed, name: "speed (km/h)", line: { color: "#1f77b4", width: 1 } }];
    if (hasHr) traces.push({ type: "scatter", mode: "lines", x: times, y: tr.hr, name: "HR (bpm)", yaxis: "y2", line: { color: "#d62728", width: 1 } });
    traces.push({
      type: "scatter", mode: "lines", x: times, y: cumKm, name: "distance (km)", yaxis: "y3", line: { color: "#2ca02c", width: 1 },
      customdata: cumPct, hovertemplate: "distance %{y:.2f} km (%{customdata:.1f}% of session)<extra></extra>",
    });
    const rect = (s, e, fill, opacity) => ({ type: "rect", xref: "x", yref: "paper", x0: times[s], x1: times[e - 1], y0: 0, y1: 1, fillcolor: fill, opacity, line: { width: 0 } });
    const shapes = state.runs.map((r, i) => rect(r.start, r.end, color(i), 0.15));
    shapes.push({ type: "line", xref: "paper", x0: 0, x1: 1, y0: state.threshold, y1: state.threshold, line: { dash: "dash", color: "#555", width: 1 } });
    for (const [s, e] of state.selected) shapes.push(rect(s, e, HIGHLIGHT, 0.25));
    Plotly.react(tlEl, traces, {
      ...plotSize("timeline", 320), margin: { l: 50, r: 50, t: 10, b: 40 }, uirevision: "timeline", hovermode: "x unified",
      legend: { orientation: "h", y: 1.12 },
      xaxis: { title: { text: `time (${state.tz})` }, domain: [0, 0.94] },
      yaxis: { title: { text: "km/h" } },
      yaxis2: { title: { text: "bpm" }, overlaying: "y", side: "right", showgrid: false },
      yaxis3: { title: { text: "km" }, overlaying: "y", side: "right", anchor: "free", position: 1, showgrid: false },
      shapes,
    });
  }

  // Run analysis plots: one dot per run, coloured like the run. Runs shorter than state.minRun are left out.
  const FIELDS = {
    run: ["Run #", String, false],
    pace_s_per_km: ["Pace (min/km)", (v) => pace(v).replace(" /km", ""), true],
    duration_s: ["Duration", duration, true],
    distance_m: ["Distance", dist, false],
    max_speed_kmh: ["Max 5 s (km/h)", num, false],
    angle_off_deg: ["Off downwind", deg, false],
    vmg_kmh: ["VMG (km/h)", num, false],
    hr_avg: ["HR avg (bpm)", int, false],
    hr_max: ["HR max (bpm)", int, false],
    back_up_s: ["Back up", duration, true],
    prev_duration_s: ["Prev run duration", duration, true],
    prev_distance_m: ["Prev run distance", dist, false],
    prev_hr_max: ["Prev run HR max (bpm)", int, false],
    hr_peak_after: ["HR peak after (bpm)", int, false],
    hr_drop_60s: ["HR drop 60 s (bpm)", int, false],
  };
  const TICK_STEPS = [5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];
  const PLOT_H = 380;
  const PLOT_FONT = { size: 10 };
  const TITLE_FONT = { size: 11 };
  const ZONE_BAR_COLORS = ["#90a4ae", "#42a5f5", "#66bb6a", "#ffca28", "#ffa726", "#ef5350"];

  const plotRows = () => state.rows.filter((r) => r.duration_s >= state.minRun);
  const plotRuns = () => state.runs.filter((r) => r.end - r.start >= state.minRun);
  const finite = (rows, ...keys) => rows.filter((r) => keys.every((k) => !missing(r[k])));
  const fixed = (v, d = 2) => (v === null || v === undefined ? "-" : v.toFixed(d));
  const pText = (p) => (p === null || p === undefined ? "-" : p < 0.001 ? "<0.001" : p.toFixed(p < 0.01 ? 3 : 2));

  // Axis settings for a field; time-like fields (seconds) get m:ss tick labels
  function axisFor(key, values) {
    const [label, , timeLike] = FIELDS[key];
    const axis = { title: { text: label } };
    if (timeLike && values.length) {
      const lo = Math.min(...values), hi = Math.max(...values);
      const step = TICK_STEPS.find((t) => (hi - lo) / t <= 6) || 3600;
      const tickvals = [];
      for (let v = Math.floor(lo / step) * step; v <= hi + step; v += step) tickvals.push(v);
      Object.assign(axis, { tickvals, ticktext: tickvals.map((v) => duration(v)) });
    }
    return axis;
  }

  const fieldText = (key, r) => `${FIELDS[key][0]}: ${FIELDS[key][1](r[key])}`;

  // "r = 0.42 (n = 17)" for the paired values; "r = -" when undefined
  function corrText(xs, ys) {
    const r = DW.pearson(xs, ys);
    return `r = ${r === null ? "-" : r.toFixed(2)} (n = ${xs.length})`;
  }

  // Smallest compass arc holding all angles, padded; as a Plotly sector (counterclockwise screen degrees, 0 = east)
  function polarSector(angles, pad = 10) {
    const a = [...new Set(angles.map((v) => ((v % 360) + 360) % 360))].sort((x, y) => x - y);
    if (a.length < 2) return [0, 360];
    let gap = 360 - a[a.length - 1] + a[0], start = a[0];
    for (let i = 1; i < a.length; i++) {
      if (a[i] - a[i - 1] > gap) { gap = a[i] - a[i - 1]; start = a[i]; }
    }
    const span = 360 - gap + 2 * pad;
    if (span > 330) return [0, 360];
    // Compass angle h is drawn at screen angle 90 - h (rotation 90, clockwise)
    const end = start - pad + span;
    return [90 - end, 90 - end + span];
  }

  // Dashed least-squares line over the x range of the points, or null
  function trendTrace(xs, ys, extra) {
    const fit = DWA.linFit(xs, ys);
    if (!fit || xs.length < 3) return null;
    const lo = Math.min(...xs), hi = Math.max(...xs);
    return Object.assign({
      type: "scatter", mode: "lines", x: [lo, hi], y: [fit.intercept + fit.slope * lo, fit.intercept + fit.slope * hi],
      line: { dash: "dash", color: "#616161", width: 1.5 }, hoverinfo: "skip", showlegend: false,
    }, extra);
  }

  const empty = (text) => ({ annotations: [{ text, showarrow: false, xref: "paper", yref: "paper", x: 0.5, y: 0.5 }],
    xaxis: { visible: false }, yaxis: { visible: false } });

  function renderScatter() {
    const xKey = document.getElementById("scatter-x").value;
    const yKey = document.getElementById("scatter-y").value;
    const rows = finite(plotRows(), xKey, yKey);
    const xs = rows.map((r) => r[xKey]), ys = rows.map((r) => r[yKey]);
    const s = DWA.corrStats(xs, ys);
    const traces = [{
      type: "scatter", mode: "markers+text", x: xs, y: ys,
      text: rows.map((r) => String(r.run)), textposition: "top center", textfont: PLOT_FONT,
      marker: { size: 10, color: rows.map((r) => color(r.run - 1)) },
      hovertext: rows.map((r) => `Run ${r.run}<br>${fieldText(xKey, r)}<br>${fieldText(yKey, r)}`), hoverinfo: "text",
    }];
    const trend = trendTrace(xs, ys);
    if (trend) traces.push(trend);
    Plotly.react("scatter", traces, {
      ...plotSize("scatter", PLOT_H), margin: { l: 55, r: 10, t: 45, b: 45 }, showlegend: false, font: PLOT_FONT,
      title: { font: TITLE_FONT, text: `Pearson r = ${fixed(s.r)} (95% CI ${fixed(s.lo)} to ${fixed(s.hi)}), p = ${pText(s.p)}`
        + `<br>Spearman ρ = ${fixed(s.rho)} · n = ${s.n}` },
      xaxis: axisFor(xKey, xs), yaxis: axisFor(yKey, ys),
    });
  }

  function renderPolar() {
    const rKey = document.getElementById("polar-r").value;
    const rows = finite(plotRows(), rKey, "heading_deg");
    const values = rows.map((r) => r[rKey]);
    const lo = Math.min(0, ...values);
    const top = Math.max(0, ...values);
    const hi = top + 0.1 * (top - lo || 1);
    const dw = DATA.meta.downwind_deg;
    const off = finite(rows, "angle_off_deg");
    Plotly.react("polar", [windArrow(lo, hi), {
      type: "scatterpolar", mode: "markers+text", showlegend: false,
      r: values, theta: rows.map((r) => r.heading_deg),
      text: rows.map((r) => String(r.run)), textposition: "top center", textfont: PLOT_FONT,
      marker: { size: 10, color: rows.map((r) => color(r.run - 1)) },
      hovertext: rows.map((r) => `Run ${r.run}<br>Heading: ${deg(r.heading_deg)}<br>${fieldText(rKey, r)}`), hoverinfo: "text",
    }], {
      ...plotSize("polar", PLOT_H), margin: { l: 30, r: 30, t: 45, b: 30 }, legend: { orientation: "h", y: -0.05 }, font: PLOT_FONT,
      title: { font: TITLE_FONT, text: `${FIELDS[rKey][0]} vs off downwind angle<br>${corrText(off.map((r) => r[rKey]), off.map((r) => r.angle_off_deg))}` },
      polar: {
        sector: polarSector([...rows.map((r) => r.heading_deg), dw]),
        angularaxis: { rotation: 90, direction: "clockwise", dtick: 45 },
        radialaxis: Object.assign(axisFor(rKey, values), { range: [lo, hi], title: { text: FIELDS[rKey][0] } }),
      },
    });
  }

  function renderZones() {
    const layout = { ...plotSize("zones", PLOT_H), margin: { l: 45, r: 10, t: 45, b: 40 }, font: PLOT_FONT, barmode: "group",
      title: { font: TITLE_FONT, text: `Time in HR zones (max HR ${state.maxHr})` },
      legend: { orientation: "h", y: -0.15 }, yaxis: { title: { text: "% of time with HR" } } };
    if (!hasHr) {
      Plotly.react("zones", [], Object.assign(layout, empty("No heart rate data")));
      return;
    }
    const z = DWA.zoneTime(tr.hr, state.runs, state.maxHr);
    const labels = ["Z0", "Z1", "Z2", "Z3", "Z4", "Z5"];
    const bar = (name, y, pattern) => ({
      type: "bar", name, x: labels, y, marker: { color: ZONE_BAR_COLORS, pattern: { shape: pattern, fgcolor: "#424242" } },
      hovertemplate: `${name}<br>%{x}: %{y:.1f}%<extra></extra>`,
    });
    Plotly.react("zones", [bar("foiling", z.foiling, ""), bar("whole session", z.session, "/")], layout);
  }

  // Variables in the correlation matrix: [field key, short label]
  const CORR_VARS = [
    ["run", "Run #"], ["pace_s_per_km", "Pace"], ["duration_s", "Duration"], ["distance_m", "Distance"],
    ["max_speed_kmh", "Max 5 s"], ["angle_off_deg", "Off downwind"], ["vmg_kmh", "VMG"], ["hr_avg", "HR avg"],
    ["hr_max", "HR max"], ["back_up_s", "Back up"], ["hr_peak_after", "HR peak after"], ["hr_drop_60s", "HR drop 60 s"],
  ];
  const corrEl = document.getElementById("corr");

  function renderCorr() {
    const rows = plotRows();
    const labels = CORR_VARS.map(([, l]) => l);
    const z = [], ns = [];
    for (const [a] of CORR_VARS) {
      const zRow = [], nRow = [];
      for (const [b] of CORR_VARS) {
        const both = finite(rows, a, b);
        zRow.push(DW.pearson(both.map((r) => r[a]), both.map((r) => r[b])));
        nRow.push(both.length);
      }
      z.push(zRow);
      ns.push(nRow);
    }
    Plotly.react(corrEl, [{
      type: "heatmap", x: labels, y: labels, z, customdata: ns, zmin: -1, zmax: 1,
      colorscale: [[0, "#2166ac"], [0.5, "#f7f7f7"], [1, "#b2182b"]],
      texttemplate: "%{z:.1f}", textfont: { size: 8 }, colorbar: { thickness: 8, len: 0.8 },
      hovertemplate: "%{y} vs %{x}<br>r = %{z:.2f}<br>n = %{customdata}<extra></extra>",
    }], {
      ...plotSize("corr", PLOT_H), margin: { l: 80, r: 5, t: 10, b: 80 }, font: { size: 9 },
      xaxis: { tickangle: -45 }, yaxis: { autorange: "reversed" },
    });
  }

  // Clicking a matrix cell loads the pair into the run scatter when it maps onto its X and Y options
  const optionValues = (id) => [...document.getElementById(id).options].map((o) => o.value);
  function bindCorrClick() {
    const keyOf = (label) => CORR_VARS.find(([, l]) => l === label)[0];
    corrEl.on("plotly_click", (ev) => {
      const a = keyOf(ev.points[0].x), b = keyOf(ev.points[0].y);
      const xs = optionValues("scatter-x"), ys = optionValues("scatter-y");
      const pair = xs.includes(a) && ys.includes(b) ? [a, b] : xs.includes(b) && ys.includes(a) ? [b, a] : null;
      if (!pair) return;
      document.getElementById("scatter-x").value = pair[0];
      document.getElementById("scatter-y").value = pair[1];
      renderScatter();
    });
  }

  function renderFatigue() {
    const rows = plotRows();
    const pRows = finite(rows, "pace_s_per_km"), hRows = finite(rows, "hr_avg"), eRows = finite(rows, "efficiency");
    const hoverOf = (r) => `Run ${r.run}<br>Pace: ${pace(r.pace_s_per_km)}<br>HR avg: ${int(r.hr_avg)}`
      + `<br>Efficiency: ${num(r.efficiency, 2)} km/h per 100 bpm`;
    const traces = [{
      type: "scatter", mode: "markers", name: "pace", x: pRows.map((r) => r.run), y: pRows.map((r) => r.pace_s_per_km),
      marker: { size: 8, color: "#1f77b4" }, hovertext: pRows.map(hoverOf), hoverinfo: "text",
    }, {
      type: "scatter", mode: "markers", name: "HR avg", yaxis: "y2", x: hRows.map((r) => r.run), y: hRows.map((r) => r.hr_avg),
      marker: { size: 8, color: "#d62728", symbol: "diamond" }, hovertext: hRows.map(hoverOf), hoverinfo: "text",
    }];
    const pTrend = trendTrace(pRows.map((r) => r.run), pRows.map((r) => r.pace_s_per_km), { line: { dash: "dash", color: "#1f77b4", width: 1.5 } });
    const hTrend = trendTrace(hRows.map((r) => r.run), hRows.map((r) => r.hr_avg), { yaxis: "y2", line: { dash: "dash", color: "#d62728", width: 1.5 } });
    for (const t of [pTrend, hTrend]) if (t) traces.push(t);
    const ex = eRows.map((r) => r.run), ey = eRows.map((r) => r.efficiency);
    const fit = DWA.linFit(ex, ey);
    const mean = ey.length ? ey.reduce((a, b) => a + b, 0) / ey.length : null;
    const pct = fit && eRows.length >= 3 && mean ? (100 * fit.slope) / mean : null;
    const effText = pct === null ? "-" : `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}% per run`;
    Plotly.react("fatigue", traces, {
      ...plotSize("fatigue", PLOT_H), margin: { l: 50, r: 45, t: 45, b: 40 }, font: PLOT_FONT, legend: { orientation: "h", y: -0.15 },
      title: { font: TITLE_FONT, text: `Efficiency trend: ${effText}<br>${corrText(ex, ey)}` },
      xaxis: { title: { text: "Run #" }, dtick: rows.length > 20 ? 5 : 1 },
      yaxis: axisFor("pace_s_per_km", pRows.map((r) => r.pace_s_per_km)),
      yaxis2: { title: { text: "HR avg (bpm)" }, overlaying: "y", side: "right", showgrid: false },
    });
  }

  // Wind arrow from the centre to radius hi, pointing downwind (compass degrees)
  function windArrow(lo, hi) {
    const dw = DATA.meta.downwind_deg;
    const head = hi - 0.12 * (hi - lo);
    return {
      type: "scatterpolar", mode: "lines", name: `downwind (wind from ${DATA.meta.wind_label})`,
      r: [lo, hi, null, head, hi, head], theta: [dw, dw, null, dw - 5, dw, dw + 5],
      line: { color: "#424242", width: 3 }, hoverinfo: "name",
    };
  }

  // Bins by signed angle off downwind, drawn at their compass heading (downwind + angle) like the run polar
  function renderAngle() {
    const bins = DWA.angleBins(tr, plotRuns());
    const layout = { ...plotSize("angle", PLOT_H), margin: { l: 30, r: 30, t: 45, b: 30 }, font: PLOT_FONT, legend: { orientation: "h", y: -0.05 } };
    if (!bins.length) {
      Plotly.react("angle", [], Object.assign(layout, empty("No samples in runs")));
      return;
    }
    const dw = DATA.meta.downwind_deg;
    const heading = (a) => (((dw + a) % 360) + 360) % 360;
    const best = bins.reduce((a, b) => (b.vmg > a.vmg ? b : a));
    const signed = (a) => `${a > 0 ? "+" : ""}${a}°`;
    const hover = bins.map((b) => `${signed(b.angle)} off downwind (heading ${deg(heading(b.angle))})`
      + `<br>avg ${num(b.avg)} km/h · best ${num(b.best)} km/h<br>VMG ${num(b.vmg)} km/h · ${b.n} s`);
    const theta = bins.map((b) => heading(b.angle));
    const hi = Math.max(...bins.map((b) => b.best)) * 1.05;
    Plotly.react("angle", [
      windArrow(0, hi),
      { type: "scatterpolar", mode: "lines+markers", name: "avg speed", r: bins.map((b) => b.avg), theta,
        line: { color: "#1f77b4" }, marker: { size: 4 }, hovertext: hover, hoverinfo: "text" },
      { type: "scatterpolar", mode: "lines+markers", name: "best speed", r: bins.map((b) => b.best), theta,
        line: { color: "#ff7f0e" }, marker: { size: 4 }, hovertext: hover, hoverinfo: "text" },
      { type: "scatterpolar", mode: "markers", name: "best VMG", r: [best.avg], theta: [heading(best.angle)],
        marker: { size: 12, color: "#2ca02c", symbol: "star" }, hoverinfo: "skip" },
    ], Object.assign(layout, {
      title: { font: TITLE_FONT, text: `Best VMG at ${signed(best.angle)} (heading ${deg(heading(best.angle))}): ${num(best.vmg)} km/h` },
      polar: {
        sector: polarSector([...theta, dw], 5),
        angularaxis: { rotation: 90, direction: "clockwise", dtick: 45 },
        radialaxis: { title: { text: "km/h" }, range: [0, hi] },
      },
    }));
  }

  function renderRunPlots() {
    renderScatter();
    renderPolar();
    renderCorr();
    renderFatigue();
    renderAngle();
  }

  // Enlarge: a card moves into a full-screen overlay, its plot is redrawn to fill it, and it moves back on close
  let expanded = null; // { card, placeholder, button }

  // Plot height: h normally; while the plot's card is enlarged, the space from the plot's top to the card's bottom
  function heightFor(id, h) {
    const el = document.getElementById(id);
    if (!expanded || !expanded.card.contains(el)) return h;
    const pad = parseFloat(getComputedStyle(expanded.card).paddingBottom) || 0;
    return Math.max(Math.floor(expanded.card.getBoundingClientRect().bottom - pad - el.getBoundingClientRect().top - 4), 200);
  }

  // Explicit width (the container's) and height for a plot: Plotly.react does not re-measure the width
  // when a plot moves into or out of the overlay, so every render passes it
  const plotSize = (id, h) => ({ width: document.getElementById(id).clientWidth || undefined, height: heightFor(id, h) });

  function openOverlay(card, button) {
    const placeholder = document.createComment("enlarged plot");
    card.replaceWith(placeholder);
    const overlay = document.createElement("div");
    overlay.className = "overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.addEventListener("click", (e) => { if (e.target === overlay) closeOverlay(); });
    overlay.appendChild(card);
    document.body.appendChild(overlay);
    document.body.classList.add("has-overlay");
    expanded = { card, placeholder, button };
    button.textContent = "✕";
    button.title = button.ariaLabel = "Close";
    renderAll(false);
    button.focus();
  }

  function closeOverlay() {
    if (!expanded) return;
    const { card, placeholder, button } = expanded;
    const overlay = card.parentElement;
    placeholder.replaceWith(card);
    overlay.remove();
    document.body.classList.remove("has-overlay");
    expanded = null;
    button.textContent = "⤢";
    button.title = button.ariaLabel = "Enlarge";
    renderAll(false);
    button.focus();
  }

  for (const card of document.querySelectorAll(".expandable")) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "expand";
    button.textContent = "⤢";
    button.title = button.ariaLabel = "Enlarge";
    button.addEventListener("click", () => (expanded ? closeOverlay() : openOverlay(card, button)));
    card.appendChild(button);
  }
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeOverlay(); });
  // Widths are explicit, so re-render on window resize (debounced)
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => renderAll(false), 150);
  });

  function renderAll(recompute) {
    if (recompute) compute();
    renderTiles();
    renderRuns();
    renderSplits();
    renderMap();
    renderTimeline();
    renderZones();
    renderRunPlots();
    syncMapHeight();
  }

  // Controls
  const thr = document.getElementById("thr");
  const thrVal = document.getElementById("thr-val");
  thrVal.textContent = state.threshold;
  thr.addEventListener("input", () => {
    state.threshold = parseFloat(thr.value);
    thrVal.textContent = thr.value;
    renderAll(true);
  });
  document.getElementById("split").addEventListener("change", (e) => {
    state.splitKm = e.target.value;
    state.selected = [];
    state.anchor = null;
    renderAll(false);
  });
  document.querySelectorAll("input[name=mode]").forEach((el) =>
    el.addEventListener("change", () => {
      state.mapMode = el.value;
      renderAll(false);
    }));

  const maxHr = document.getElementById("max-hr");
  maxHr.addEventListener("change", () => {
    const v = Number(maxHr.value);
    if (Number.isInteger(v) && v > 0) {
      state.maxHr = v;
      renderRuns();
      renderSplits();
      renderZones();
    } else {
      maxHr.value = state.maxHr;
    }
  });

  bearingInput.addEventListener("input", () => setBearing(Number(bearingInput.value)));
  document.getElementById("bearing-auto").addEventListener("click", () => setBearing(autoBearing));
  document.getElementById("bearing-north").addEventListener("click", () => setBearing(0));

  // One "Min run" box per run analysis plot, all sharing state.minRun
  const minRunInputs = document.querySelectorAll(".min-run input");
  for (const input of minRunInputs) {
    input.addEventListener("change", () => {
      const v = Number(input.value);
      if (Number.isInteger(v) && v >= 0) state.minRun = v;
      for (const other of minRunInputs) other.value = state.minRun;
      renderRunPlots();
    });
  }

  document.getElementById("scatter-x").addEventListener("change", renderScatter);
  document.getElementById("scatter-y").addEventListener("change", renderScatter);
  document.getElementById("polar-r").addEventListener("change", renderPolar);

  const tzSelect = document.getElementById("tz");
  const zones = new Set(typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : []);
  zones.add("UTC");
  zones.add(DATA.meta.tz);
  for (const z of [...zones].sort()) tzSelect.add(new Option(z, z, false, z === DATA.meta.tz));
  tzSelect.addEventListener("change", () => {
    setTimeZone(tzSelect.value);
    renderAll(false);
  });

  setTimeZone(DATA.meta.tz);
  renderAll(true);
  bindCorrClick();
  // Rotating the map by dragging updates the slider and the north arrow
  mapEl.on("plotly_relayout", (ev) => {
    if (ev["map.bearing"] !== undefined) showBearing(Math.round(((ev["map.bearing"] + 540) % 360) - 180));
  });
  if (typeof ResizeObserver === "function") new ResizeObserver(syncMapHeight).observe(rightCol);
})();
