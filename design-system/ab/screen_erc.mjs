import { validate, contrast } from "file:///C:/Users/theod/AppData/Local/Temp/claude/bundled-skills/2.1.250/7d34fd5c5ca02f9d932830007398ac3e/dataviz/scripts/validate_palette.js";
const SURF = "#FFFFFF";
const num = s => { const m = /ΔE ([0-9.]+)/.exec(s); return m ? +m[1] : NaN; };
function pair(a, b) {
  const r = validate([a, b], { mode: "light", surface: SURF, pairs: "all" });
  const rows = Object.fromEntries(r.report.map(x => [x[0], x[2]]));
  return { normal: num(rows["Normal-vision floor"]), cvd: num(rows["CVD separation"]) };
}
const OA = { "Life #0CA750": "#0CA750", "Social #FFCB3A": "#FFCB3A", "Physical #8190FF": "#8190FF", "Health #F85C32": "#F85C32" };
const cands = process.argv.slice(2);
for (const c of cands) {
  let worstN = 99, worstC = 99, wn = "", wc = "";
  for (const [k, o] of Object.entries(OA)) {
    const p = pair(c, o);
    if (p.normal < worstN) { worstN = p.normal; wn = k; }
    if (p.cvd < worstC) { worstC = p.cvd; wc = k; }
  }
  console.log(`${c}  vsOA minNormal=${worstN.toFixed(1)} (${wn})  minCVD=${worstC.toFixed(1)} (${wc})  contrast=${contrast(c, SURF).toFixed(2)}`);
}
