// Stream VS3 (2B-R2-2): WHICH ERC domain gets which of the three ruled hues.
// The legality of the trio is NOT open (palette_validation.txt run 13: ALL
// CHECKS PASS, no warning) -- only the assignment is, and it is scored here
// against the ONE thing that can make an assignment wrong: what a reader who
// has just scrolled a Find page full of OA-domain colour will read into it.
//
// Score per permutation = sum over the three ERC domains of
//     (mean normal-vision distance to the OA domains that mean something ELSE)
//   - (normal-vision distance to the OA domain that means the SAME thing)
// so a high score is a trio whose hues sit CLOSE to their semantic twin in the
// OA palette and FAR from the OA domains they could be confused with.
// Throwaway, design-system/ab/** only.
import { validate } from "file:///C:/Users/theod/AppData/Local/Temp/claude/bundled-skills/2.1.251/06f447984e7673a25ccfaa2ab5a9cf1e/dataviz/scripts/validate_palette.js";

const SURF = "#FFFFFF";
const num = s => { const m = /ΔE ([0-9.]+)/.exec(s); return m ? +m[1] : NaN; };
function dE(a, b) {
  const r = Object.fromEntries(validate([a, b], { mode: "light", surface: SURF, pairs: "all" })
    .report.map(x => [x[0], x[2]]));
  return { normal: num(r["Normal-vision floor"]), cvd: num(r["CVD separation"]) };
}
const OA = { Life: "#0CA750", Social: "#FFCB3A", Physical: "#8190FF", Health: "#F85C32" };
// the OA domain each ERC domain MEANS the same thing as
const TWIN = { PE: "Physical", LS: "Life", SH: "Social" };
const HUES = ["#D55E00", "#009E73", "#6A3D9A"];
const NAME = { "#D55E00": "vermillion", "#009E73": "bluish green", "#6A3D9A": "violet" };
const INST = (process.argv[2] || "#FF8BA6,#B4BF07,#8EB3FF").split(",");

function perms(a) {
  if (a.length <= 1) return [a];
  return a.flatMap((x, i) => perms([...a.slice(0, i), ...a.slice(i + 1)]).map(p => [x, ...p]));
}
const rows = [];
for (const p of perms(HUES)) {
  const map = { PE: p[0], LS: p[1], SH: p[2] };
  let score = 0;
  const detail = [];
  for (const d of ["PE", "LS", "SH"]) {
    const same = dE(map[d], OA[TWIN[d]]).normal;
    const others = Object.entries(OA).filter(([k]) => k !== TWIN[d]).map(([, h]) => dE(map[d], h).normal);
    const mean = others.reduce((a, b) => a + b, 0) / others.length;
    score += mean - same;
    detail.push(`${d}=${NAME[map[d]]} (twin ${same.toFixed(1)}, others ${mean.toFixed(1)})`);
  }
  rows.push({ map, score, detail });
}
rows.sort((a, b) => b.score - a.score);
for (const r of rows)
  console.log(`  score ${r.score.toFixed(1).padStart(6)}   PE ${r.map.PE} LS ${r.map.LS} SH ${r.map.SH}   ${r.detail.join(" | ")}`);

console.log("=== the new ERC trio vs the new institution trio (run-17 class: accent glyph vs bar) ===");
let mn = 99, mc = 99, arg = "";
for (const e of HUES) for (const i of INST) {
  const p = dE(e, i);
  if (p.normal < mn) { mn = p.normal; arg = `${e}<->${i}`; }
  mc = Math.min(mc, p.cvd);
}
console.log(`  min normal ${mn.toFixed(1)}  min cvd ${mc.toFixed(1)}  (${arg})`);
console.log("=== the new ERC trio vs the OLD one it replaces (sequential memory) ===");
for (const [a, b] of [["#D55E00", "#1F4E9C"], ["#009E73", "#9B1B6B"], ["#6A3D9A", "#8A5A00"]])
  console.log(`  ${a} <-> ${b}  normal ${dE(a, b).normal.toFixed(1)}`);
