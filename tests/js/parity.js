// Usage: node parity.js <path to runs.js>  (JSON input on stdin)
const DW = require(process.argv[2]);
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = input.thresholds.map((thr) => {
  const runs = DW.detectRuns(input.track.speed, thr, input.min_duration_s, input.merge_gap_s);
  return { runs, rows: DW.runRows(input.track, runs), foil: DW.foilStats(input.track, runs) };
});
process.stdout.write(JSON.stringify(out));
