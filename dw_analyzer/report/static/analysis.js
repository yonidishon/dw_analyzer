// Run analysis statistics: correlations, trends, per-run extras, angle bins, HR zone time.
(function (root) {
  "use strict";

  const ok = (v) => v !== null && v !== undefined && Number.isFinite(v);
  const HR_ZONES_PCT = [50, 60, 70, 80, 90]; // lower bounds of Z1-Z5 in % of max HR (metrics.py)

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

  // Average ranks, 1-based; ties share the mean of their positions.
  function ranks(xs) {
    const idx = xs.map((_, i) => i).sort((a, b) => xs[a] - xs[b]);
    const out = new Array(xs.length);
    let i = 0;
    while (i < idx.length) {
      let j = i;
      while (j + 1 < idx.length && xs[idx[j + 1]] === xs[idx[i]]) j++;
      const rank = (i + j) / 2 + 1;
      for (let k = i; k <= j; k++) out[idx[k]] = rank;
      i = j + 1;
    }
    return out;
  }

  const spearman = (xs, ys) => pearson(ranks(xs), ranks(ys));

  function lgamma(x) {
    const c = [76.18009172947146, -86.50532032941677, 24.01409824083091,
      -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
    let y = x, tmp = x + 5.5;
    tmp -= (x + 0.5) * Math.log(tmp);
    let ser = 1.000000000190015;
    for (let j = 0; j < 6; j++) ser += c[j] / ++y;
    return -tmp + Math.log(2.5066282746310005 * ser / x);
  }

  // Continued fraction for the incomplete beta function (modified Lentz).
  function betacf(a, b, x) {
    const FPMIN = 1e-300, EPS = 3e-16;
    const qab = a + b, qap = a + 1, qam = a - 1;
    let c = 1, d = 1 - qab * x / qap;
    if (Math.abs(d) < FPMIN) d = FPMIN;
    d = 1 / d;
    let h = d;
    for (let m = 1; m <= 300; m++) {
      const m2 = 2 * m;
      let aa = m * (b - m) * x / ((qam + m2) * (a + m2));
      d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
      c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
      d = 1 / d; h *= d * c;
      aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2));
      d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
      c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
      d = 1 / d;
      const del = d * c;
      h *= del;
      if (Math.abs(del - 1) < EPS) break;
    }
    return h;
  }

  // Regularised incomplete beta I_x(a, b).
  function ibeta(x, a, b) {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    const bt = Math.exp(lgamma(a + b) - lgamma(a) - lgamma(b) + a * Math.log(x) + b * Math.log(1 - x));
    return x < (a + 1) / (a + b + 2) ? bt * betacf(a, b, x) / a : 1 - bt * betacf(b, a, 1 - x) / b;
  }

  // Two-sided p of Student's t with df degrees of freedom.
  const pTwoSided = (t, df) => ibeta(df / (df + t * t), df / 2, 0.5);

  function corrStats(xs, ys) {
    const n = xs.length;
    const out = { n, r: null, p: null, lo: null, hi: null, rho: null };
    out.r = pearson(xs, ys);
    out.rho = spearman(xs, ys);
    if (out.r === null) return out;
    const r = out.r, full = Math.abs(r) >= 1;
    if (n >= 3) out.p = full ? 0 : pTwoSided(r * Math.sqrt((n - 2) / (1 - r * r)), n - 2);
    if (n >= 4 && !full) {
      const z = Math.atanh(r), se = 1 / Math.sqrt(n - 3);
      out.lo = Math.tanh(z - 1.959964 * se);
      out.hi = Math.tanh(z + 1.959964 * se);
    }
    return out;
  }

  // Least-squares y on x.
  function linFit(xs, ys) {
    const n = xs.length;
    if (n < 2) return null;
    const mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
    let sxy = 0, sxx = 0;
    for (let i = 0; i < n; i++) {
      sxy += (xs[i] - mx) * (ys[i] - my); sxx += (xs[i] - mx) * (xs[i] - mx);
    }
    if (!(sxx > 0)) return null;
    const slope = sxy / sxx;
    return { slope, intercept: my - slope * mx };
  }

  // Adds previous-run fields, post-run HR peak/drop and efficiency to rows in place.
  function runExtras(tr, runs, rows) {
    const hr = tr.hr, n = hr.length;
    rows.forEach((row, i) => {
      const prev = i > 0 ? rows[i - 1] : null;
      row.prev_duration_s = prev ? prev.duration_s : null;
      row.prev_distance_m = prev ? prev.distance_m : null;
      row.prev_hr_max = prev ? prev.hr_max : null;
      const next = i + 1 < runs.length ? runs[i + 1].start : null;
      const stop = Math.min(runs[i].end + 60, next === null ? n : next, n);
      let peakIdx = -1;
      for (let k = runs[i].end; k < stop; k++) {
        if (ok(hr[k]) && (peakIdx < 0 || hr[k] > hr[peakIdx])) peakIdx = k;
      }
      row.hr_peak_after = peakIdx < 0 ? null : hr[peakIdx];
      const after = peakIdx + 60;
      row.hr_drop_60s = peakIdx < 0 || after >= n || (next !== null && after >= next) || !ok(hr[after])
        ? null : hr[peakIdx] - hr[after];
      row.efficiency = ok(row.hr_avg) && ok(row.avg_speed_kmh) && row.hr_avg > 0
        ? row.avg_speed_kmh / row.hr_avg * 100 : null;
    });
  }

  // Speed statistics per signed angle-off-downwind bin, inside the given runs only.
  function angleBins(tr, runs, binDeg = 5, minSamples = 5) {
    const bins = new Map();
    for (const run of runs) {
      for (let i = run.start; i < run.end; i++) {
        if ((tr.gap && tr.gap[i]) || !ok(tr.speed[i]) || !ok(tr.angle_off[i])) continue;
        const centre = Math.floor(tr.angle_off[i] / binDeg) * binDeg + binDeg / 2;
        let b = bins.get(centre);
        if (!b) bins.set(centre, (b = { sum: 0, best: -Infinity, n: 0 }));
        b.sum += tr.speed[i]; b.n++;
        if (tr.speed[i] > b.best) b.best = tr.speed[i];
      }
    }
    return [...bins.entries()].filter(([, b]) => b.n >= minSamples).sort((a, b) => a[0] - b[0])
      .map(([angle, b]) => {
        const avg = b.sum / b.n;
        return { angle, avg, best: b.best, vmg: avg * Math.cos(angle * Math.PI / 180), n: b.n };
      });
  }

  // Percent of samples with HR per zone Z0-Z5, inside runs and over the whole session.
  function zoneTime(hr, runs, maxHr) {
    const zero = () => [0, 0, 0, 0, 0, 0];
    const foiling = zero(), session = zero();
    if (!(maxHr > 0)) return { foiling, session };
    const inRun = new Uint8Array(hr.length);
    for (const run of runs) inRun.fill(1, run.start, run.end);
    for (let i = 0; i < hr.length; i++) {
      if (!ok(hr[i])) continue;
      const pct = hr[i] / maxHr * 100;
      const z = HR_ZONES_PCT.filter((b) => pct >= b).length;
      session[z]++;
      if (inRun[i]) foiling[z]++;
    }
    const norm = (a) => {
      const total = a.reduce((x, y) => x + y, 0);
      return total ? a.map((v) => v / total * 100) : a;
    };
    return { foiling: norm(foiling), session: norm(session) };
  }

  const DWA = { pearson, ranks, spearman, pTwoSided, corrStats, linFit, runExtras, angleBins, zoneTime };
  if (typeof module !== "undefined" && module.exports) module.exports = DWA;
  else root.DWA = DWA;
})(this);
