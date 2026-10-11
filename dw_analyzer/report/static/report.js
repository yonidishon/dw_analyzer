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

  const state = { threshold: DATA.params.threshold_kmh, splitKm: "1", mapMode: "speed", tz: DATA.meta.tz, maxHr: DATA.params.max_hr, highlight: null, runs: [], rows: [], overall: {}, sort: { key: "run", desc: false }, splitSort: { key: "split", desc: false } };

  function compute() {
    state.runs = DW.detectRuns(tr.speed, state.threshold, DATA.params.min_duration_s, DATA.params.merge_gap_s, tr.gap);
    state.rows = DW.runRows(tr, state.runs);
    for (const r of state.rows) r.distance_pct = DATA.overall.distance_m > 0 ? (100 * r.distance_m) / DATA.overall.distance_m : null;
    state.overall = Object.assign({}, DATA.overall, DW.foilStats(tr, state.runs));
    state.highlight = null;
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

  const RUN_COLS = [
    ["#", (r) => String(r.run), "run", false],
    ["Start", (r) => clock(r.start_t)],
    ["Duration", (r) => duration(r.duration_s), "duration_s", true],
    ["Distance / % of run", (r) => `${dist(r.distance_m)} / ${num(r.distance_pct, 0)}%`, "distance_m", true],
    ["Avg km/h", (r) => num(r.avg_speed_kmh)],
    ["Pace", (r) => pace(r.pace_s_per_km), "pace_s_per_km", false],
    ["Max 5 s", (r) => num(r.max_speed_kmh), "max_speed_kmh", true],
    ["Heading", (r) => deg(r.heading_deg)],
    ["Off downwind", (r) => deg(r.angle_off_deg)],
    ["VMG km/h", (r) => num(r.vmg_kmh)],
    ["HR avg", (r) => int(r.hr_avg), "hr_avg", true],
    ["HR max", (r) => int(r.hr_max), "hr_max", true],
    ["HR zone", (r) => hrZoneText(r.hr_avg)],
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
    ["HR zone", (r) => hrZoneText(r.hr_avg)],
  ];

  const isHighlighted = (s, e) => state.highlight && state.highlight[0] === s && state.highlight[1] === e;

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
  function renderTable(el, cols, rows, swatch, sort, onSort) {
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
      cols.forEach(([, f], c) => {
        const td = row.insertCell();
        td.textContent = f(r);
        if (c === 0 && swatch) td.style.borderLeft = `6px solid ${color(r.run - 1)}`;
      });
      if (isHighlighted(r.start_t, r.end_t)) row.classList.add("selected");
      row.addEventListener("click", () => {
        state.highlight = isHighlighted(r.start_t, r.end_t) ? null : [r.start_t, r.end_t];
        renderAll(false);
      });
    });
    el.replaceChildren(table);
  }

  function renderSplits() {
    const s = state.splitSort;
    renderTable(document.getElementById("splits"), SPLIT_COLS, DW.sortRows(DATA.splits[state.splitKm], s.key, s.desc), false, s, (next) => {
      state.splitSort = next;
      renderSplits();
    });
  }

  function renderRuns() {
    const el = document.getElementById("runs");
    if (state.rows.length) {
      renderTable(el, RUN_COLS, DW.sortRows(state.rows, state.sort.key, state.sort.desc), true, state.sort, (s) => {
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
  const bounds = { latMin: Math.min(...lats), latMax: Math.max(...lats), lonMin: Math.min(...lons), lonMax: Math.max(...lons) };
  const center = { lat: (bounds.latMin + bounds.latMax) / 2, lon: (bounds.lonMin + bounds.lonMax) / 2 };

  // Same formula as fit_zoom() in figures.py
  function fitZoom(w, h) {
    const lonSpan = Math.max(bounds.lonMax - bounds.lonMin, 1e-3);
    const latSpan = Math.max((bounds.latMax - bounds.latMin) / Math.cos((center.lat * Math.PI) / 180), 1e-3);
    const z = Math.min(Math.log2((360 * w) / 512 / lonSpan), Math.log2((360 * h) / 512 / latSpan));
    return Math.min(z - 0.4, 16);
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
    if (state.highlight) traces.push(line(state.highlight[0], state.highlight[1], HIGHLIGHT, 7, "selected", false));
    return traces;
  }

  function renderMap() {
    const h = 560;
    const w = mapEl.clientWidth || 800;
    Plotly.react(mapEl, mapTraces(), {
      height: h, margin: { l: 0, r: 0, t: 0, b: 0 }, showlegend: false, uirevision: "map",
      map: { style: "carto-voyager", center, zoom: fitZoom(w, h) },
    }, { responsive: true });
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
    if (state.highlight) shapes.push(rect(state.highlight[0], state.highlight[1], HIGHLIGHT, 0.25));
    Plotly.react(tlEl, traces, {
      height: 320, margin: { l: 50, r: 50, t: 10, b: 40 }, uirevision: "timeline", hovermode: "x unified",
      legend: { orientation: "h", y: 1.12 },
      xaxis: { title: { text: `time (${state.tz})` }, domain: [0, 0.94] },
      yaxis: { title: { text: "km/h" } },
      yaxis2: { title: { text: "bpm" }, overlaying: "y", side: "right", showgrid: false },
      yaxis3: { title: { text: "km" }, overlaying: "y", side: "right", anchor: "free", position: 1, showgrid: false },
      shapes,
    }, { responsive: true });
  }

  // Run analysis plots: one dot per run, coloured like the run
  const FIELDS = {
    pace_s_per_km: ["Pace (min/km)", (v) => pace(v).replace(" /km", ""), true],
    duration_s: ["Duration", duration, true],
    distance_m: ["Distance", dist, false],
    hr_avg: ["HR avg (bpm)", int, false],
    hr_max: ["HR max (bpm)", int, false],
    back_up_s: ["Back up", duration, true],
    vmg_kmh: ["VMG (km/h)", num, false],
  };
  const TICK_STEPS = [5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];

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
  function polarSector(angles) {
    const a = [...new Set(angles.map((v) => ((v % 360) + 360) % 360))].sort((x, y) => x - y);
    if (a.length < 2) return [0, 360];
    let gap = 360 - a[a.length - 1] + a[0], start = a[0];
    for (let i = 1; i < a.length; i++) {
      if (a[i] - a[i - 1] > gap) { gap = a[i] - a[i - 1]; start = a[i]; }
    }
    const span = 360 - gap + 20;
    if (span > 330) return [0, 360];
    // Compass heading h is drawn at screen angle 90 - h (rotation 90, clockwise)
    const end = start - 10 + span;
    return [90 - end, 90 - end + span];
  }

  function renderScatter() {
    const xKey = document.getElementById("scatter-x").value;
    const yKey = document.getElementById("scatter-y").value;
    const rows = state.rows.filter((r) => !missing(r[xKey]) && !missing(r[yKey]));
    Plotly.react("scatter", [{
      type: "scatter", mode: "markers+text",
      x: rows.map((r) => r[xKey]), y: rows.map((r) => r[yKey]),
      text: rows.map((r) => String(r.run)), textposition: "top center",
      marker: { size: 11, color: rows.map((r) => color(r.run - 1)) },
      hovertext: rows.map((r) => `Run ${r.run}<br>${fieldText(xKey, r)}<br>${fieldText(yKey, r)}`), hoverinfo: "text",
    }], {
      height: 420, margin: { l: 60, r: 20, t: 40, b: 50 }, showlegend: false,
      title: { text: corrText(rows.map((r) => r[xKey]), rows.map((r) => r[yKey])), font: { size: 13 } },
      xaxis: axisFor(xKey, rows.map((r) => r[xKey])),
      yaxis: axisFor(yKey, rows.map((r) => r[yKey])),
    }, { responsive: true });
  }

  function offPairs(rows, key) {
    const both = rows.filter((r) => !missing(r.angle_off_deg));
    return [both.map((r) => r[key]), both.map((r) => r.angle_off_deg)];
  }

  function renderPolar() {
    const rKey = document.getElementById("polar-r").value;
    const rows = state.rows.filter((r) => !missing(r[rKey]) && !missing(r.heading_deg));
    const values = rows.map((r) => r[rKey]);
    const lo = Math.min(0, ...values);
    const top = Math.max(0, ...values);
    const hi = top + 0.1 * (top - lo || 1);
    const dw = DATA.meta.downwind_deg;
    const head = hi - 0.12 * (hi - lo);
    Plotly.react("polar", [{
      // Static wind arrow from the centre, pointing downwind
      type: "scatterpolar", mode: "lines", name: `downwind (wind from ${DATA.meta.wind_label})`,
      r: [lo, hi, null, head, hi, head], theta: [dw, dw, null, dw - 5, dw, dw + 5],
      line: { color: "#424242", width: 3 }, hoverinfo: "name",
    }, {
      type: "scatterpolar", mode: "markers+text", showlegend: false,
      r: values, theta: rows.map((r) => r.heading_deg),
      text: rows.map((r) => String(r.run)), textposition: "top center",
      marker: { size: 11, color: rows.map((r) => color(r.run - 1)) },
      hovertext: rows.map((r) => `Run ${r.run}<br>Heading: ${deg(r.heading_deg)}<br>${fieldText(rKey, r)}`), hoverinfo: "text",
    }], {
      height: 420, margin: { l: 40, r: 40, t: 40, b: 30 }, legend: { orientation: "h", y: -0.05 },
      title: { text: `${FIELDS[rKey][0]} vs off downwind angle: ${corrText(...offPairs(rows, rKey))}`, font: { size: 13 } },
      polar: {
        sector: polarSector([...rows.map((r) => r.heading_deg), dw]),
        angularaxis: { rotation: 90, direction: "clockwise", dtick: 45 },
        radialaxis: Object.assign(axisFor(rKey, values), { range: [lo, hi], title: { text: FIELDS[rKey][0] } }),
      },
    }, { responsive: true });
  }

  function renderAll(recompute) {
    if (recompute) compute();
    renderTiles();
    renderRuns();
    renderSplits();
    renderMap();
    renderTimeline();
    renderScatter();
    renderPolar();
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
    state.highlight = null;
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
    } else {
      maxHr.value = state.maxHr;
    }
  });

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
})();
