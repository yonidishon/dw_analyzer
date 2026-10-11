// Run detection and run statistics. Mirrors dw_analyzer/runs.py and dw_analyzer/metrics.py.
(function (root) {
  "use strict";

  const ok = (v) => v !== null && v !== undefined && Number.isFinite(v);

  // Samples flagged in gap (GPS dropouts) never count as above the threshold.
  function detectRuns(speed, threshold, minDuration, mergeGap, gap) {
    const above = (i) => ok(speed[i]) && speed[i] > threshold && !(gap && gap[i]);
    const segments = [];
    let i = 0;
    while (i < speed.length) {
      if (above(i)) {
        let j = i;
        while (j < speed.length && above(j)) j++;
        segments.push([i, j]);
        i = j;
      } else {
        i++;
      }
    }
    const merged = [];
    for (const [s, e] of segments) {
      if (merged.length && s - merged[merged.length - 1][1] < mergeGap) merged[merged.length - 1][1] = e;
      else merged.push([s, e]);
    }
    return merged.filter(([s, e]) => e - s >= minDuration).map(([s, e]) => ({ start: s, end: e }));
  }

  function mean(a, s, e, f) {
    let sum = 0, n = 0;
    for (let i = s; i < e; i++) if (ok(a[i])) { sum += f ? f(a[i]) : a[i]; n++; }
    return n ? sum / n : null;
  }

  function max(a, s, e) {
    let m = null;
    for (let i = s; i < e; i++) if (ok(a[i]) && (m === null || a[i] > m)) m = a[i];
    return m;
  }

  function circMean(a, s, e) {
    let sx = 0, cy = 0, n = 0;
    for (let i = s; i < e; i++) {
      if (!ok(a[i])) continue;
      const r = (a[i] * Math.PI) / 180;
      sx += Math.sin(r); cy += Math.cos(r); n++;
    }
    if (!n) return null;
    const d = (Math.atan2(sx / n, cy / n) * 180) / Math.PI;
    return ((d % 360) + 360) % 360;
  }

  function bestTimeWindow(speed, gap, s, e, w) {
    let best = null;
    for (let i = s; i + w <= e; i++) {
      let sum = 0, clean = true;
      for (let k = i; k < i + w; k++) {
        if (gap[k]) { clean = false; break; }
        sum += speed[k];
      }
      if (clean && (best === null || sum / w > best)) best = sum / w;
    }
    return best;
  }

  function segmentStats(tr, s, e) {
    const dur = e - s;
    let dist = 0;
    for (let i = s; i < e; i++) dist += tr.step[i];
    const avg = dur ? (dist / dur) * 3.6 : null;
    return {
      duration_s: dur,
      distance_m: dist,
      avg_speed_kmh: avg,
      pace_s_per_km: avg > 0 ? 3600 / avg : null,
      max_speed_kmh: bestTimeWindow(tr.speed, tr.gap, s, e, 5),
      heading_deg: circMean(tr.heading, s, e),
      angle_off_deg: mean(tr.angle_off, s, e, Math.abs),
      vmg_kmh: mean(tr.vmg, s, e),
      hr_avg: mean(tr.hr, s, e),
      hr_max: max(tr.hr, s, e),
    };
  }

  function runRows(tr, runs) {
    return runs.map((r, i) => Object.assign(
      { run: i + 1, start_t: r.start, end_t: r.end, back_up_s: i ? r.start - runs[i - 1].end : null },
      segmentStats(tr, r.start, r.end),
    ));
  }

  const BEST_RUN_MIN_S = 60; // shorter runs do not compete for "best run" (metrics.py)
  const runPace = (r) => (r && r.dist > 0 ? (r.dur / r.dist) * 1000 : null);

  function foilStats(tr, runs) {
    let t = 0, dist = 0, vmgSum = 0, vmgN = 0;
    let longest = null, best = null;
    for (const r of runs) {
      let runDist = 0;
      for (let i = r.start; i < r.end; i++) {
        runDist += tr.step[i];
        if (ok(tr.vmg[i])) { vmgSum += tr.vmg[i]; vmgN++; }
      }
      t += r.end - r.start;
      dist += runDist;
      const run = { dur: r.end - r.start, dist: runDist };
      if (longest === null || run.dur > longest.dur) longest = run;
      if (run.dur >= BEST_RUN_MIN_S && (best === null || run.dist / run.dur > best.dist / best.dur)) best = run;
    }
    const gaps = runs.slice(1).map((r, i) => r.start - runs[i].end);
    const avg = t ? (dist / t) * 3.6 : null;
    return {
      n_runs: runs.length,
      time_foiling_s: t,
      pct_foiling: (100 * t) / tr.speed.length,
      avg_speed_foiling_kmh: avg,
      pace_foiling_s_per_km: avg > 0 ? 3600 / avg : null,
      vmg_foiling_kmh: vmgN ? vmgSum / vmgN : null,
      longest_run_s: longest ? longest.dur : null,
      longest_run_m: longest ? longest.dist : null,
      longest_run_pace_s_per_km: runPace(longest),
      best_run_s: best ? best.dur : null,
      best_run_m: best ? best.dist : null,
      best_run_pace_s_per_km: runPace(best),
      avg_gap_s: gaps.length ? gaps.reduce((a, b) => a + b, 0) / gaps.length : null,
      max_gap_s: gaps.length ? Math.max(...gaps) : null,
    };
  }

  // Sorted copy of rows by key; missing values always last; ties keep their original order.
  function sortRows(rows, key, desc) {
    return rows
      .map((r, i) => [r, i])
      .sort(([a, i], [b, k]) => {
        const va = a[key], vb = b[key];
        if (!ok(va) || !ok(vb)) return ok(va) ? -1 : ok(vb) ? 1 : i - k;
        return (desc ? vb - va : va - vb) || i - k;
      })
      .map(([r]) => r);
  }

  // Pearson correlation of paired values; null for fewer than 3 pairs or a constant series
  function pearson(xs, ys) {
    const n = xs.length;
    if (n < 3) return null;
    const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
    let sxy = 0, sxx = 0, syy = 0;
    for (let i = 0; i < n; i++) {
      const dx = xs[i] - mx, dy = ys[i] - my;
      sxy += dx * dy; sxx += dx * dx; syy += dy * dy;
    }
    return sxx > 0 && syy > 0 ? sxy / Math.sqrt(sxx * syy) : null;
  }

  const HR_ZONES_PCT = [50, 60, 70, 80, 90]; // lower bounds of Z1-Z5 in % of max HR (metrics.py)
  const hrZone = (pct) => (ok(pct) ? HR_ZONES_PCT.filter((b) => pct >= b).length : null);

  const DW = { detectRuns, segmentStats, runRows, foilStats, sortRows, pearson, hrZone };
  if (typeof module !== "undefined" && module.exports) module.exports = DW;
  else root.DW = DW;
})(this);
