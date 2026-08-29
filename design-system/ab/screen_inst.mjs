// Stream V (Phase 2B): full pairwise matrix for a candidate INSTITUTION_COLORS
// set, plus every candidate's distance to FOCAL and COMPARISON. Throwaway
// screening tool, design-system/ab/** only -- the shipped evidence is the
// validator log in design-system/palette_validation.txt.
import { validate, contrast } from "file:///C:/Users/theod/AppData/Local/Temp/claude/bundled-skills/2.1.250/7d34fd5c5ca02f9d932830007398ac3e/dataviz/scripts/validate_palette.js";
const SURF = "#FFFFFF";
const num = s => { const m = /ΔE ([0-9.]+)/.exec(s); return m ? +m[1] : NaN; };
function pair(a, b) {
  const r = validate([a, b], { mode: "light", surface: SURF, pairs: "all" });
  const rows = Object.fromEntries(r.report.map(x => [x[0], x[2]]));
  return { normal: num(rows["Normal-vision floor"]), cvd: num(rows["CVD separation"]) };
}
const set = process.argv[2].split(",");
console.log("pairwise (normal / worst-CVD):");
let wn = 99, wc = 99, wnp = "", wcp = "";
for (let i = 0; i < set.length; i++) for (let j = i + 1; j < set.length; j++) {
  const p = pair(set[i], set[j]);
  console.log(`  ${i + 1}-${j + 1}  ${set[i]} <-> ${set[j]}   normal ${p.normal.toFixed(1)}   cvd ${p.cvd.toFixed(1)}`);
  if (p.normal < wn) { wn = p.normal; wnp = `${set[i]}<->${set[j]}`; }
  if (p.cvd < wc) { wc = p.cvd; wcp = `${set[i]}<->${set[j]}`; }
}
console.log(`worst normal ${wn.toFixed(1)} (${wnp}) | worst cvd ${wc.toFixed(1)} (${wcp})`);
console.log("contrast vs surface + distance to chrome:");
for (const c of set) {
  const f = pair(c, "#0072B2"), g = pair(c, "#8C9196");
  console.log(`  ${c} contrast ${contrast(c, SURF).toFixed(2)}  vsFOCAL normal ${f.normal.toFixed(1)} cvd ${f.cvd.toFixed(1)}  vsCOMPARISON normal ${g.normal.toFixed(1)} cvd ${g.cvd.toFixed(1)}`);
}
