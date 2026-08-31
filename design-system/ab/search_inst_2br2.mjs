// Stream VS3: hue fine-tuning search inside the A1 window L in [0.74, 0.77].
// Scores every hue triple (6 deg step) that the validator returns ok=true for,
// by (worst in-trio CVD, worst in-trio normal, min normal distance to OA+SDG).
// Throwaway, design-system/ab/** only.
import { validate } from "file:///C:/Users/theod/AppData/Local/Temp/claude/bundled-skills/2.1.251/06f447984e7673a25ccfaa2ab5a9cf1e/dataviz/scripts/validate_palette.js";

const SURF = "#FFFFFF";
const num = s => { const m = /ΔE ([0-9.]+)/.exec(s); return m ? +m[1] : NaN; };
const rep = r => Object.fromEntries(r.report.map(x => [x[0], x[2]]));
function pair(a, b) {
  const r = rep(validate([a, b], { mode: "light", surface: SURF, pairs: "all" }));
  return { normal: num(r["Normal-vision floor"]), cvd: num(r["CVD separation"]) };
}
const s2lin = c => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const lin2s = c => { c = Math.max(0, Math.min(1, c)); return c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055; };
function lchToLinear(L, C, H) {
  const a = C * Math.cos(H * Math.PI / 180), b = C * Math.sin(H * Math.PI / 180);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
  return [+4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
          -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
          -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
}
const inGamut = rgb => rgb.every(v => v >= -1e-4 && v <= 1 + 1e-4);
const toHex = rgb => "#" + rgb.map(v => Math.round(lin2s(v) * 255).toString(16).padStart(2, "0").toUpperCase()).join("");
function maxChromaHex(L, H) {                 // most saturated in-gamut colour at (L, H)
  let c = 0.37;
  while (c > 0 && !inGamut(lchToLinear(L, c, H))) c -= 0.002;
  return { hex: toHex(lchToLinear(L, c, H)), c };
}
const CHROME = ["#0072B2", "#8C9196", "#C2185B"];
const OA = ["#0CA750", "#FFCB3A", "#8190FF", "#F85C32"];
const SDG = ["#E5243B", "#DDA63A", "#4C9F38", "#C5192D", "#FF3A21", "#26BDE2", "#FCC30B",
             "#A21942", "#FD6925", "#DD1367", "#FD9D24", "#BF8B2E", "#3F7E44", "#0A97D9",
             "#56C02B", "#00689D"];

const best = [];
for (const L of [0.740, 0.750, 0.760, 0.770]) {
  const ring = [];
  for (let H = 0; H < 360; H += 6) {
    const { hex, c } = maxChromaHex(L, H);
    if (c >= 0.1) ring.push({ H, hex });
  }
  for (let i = 0; i < ring.length; i++)
    for (let j = i + 1; j < ring.length; j++)
      for (let k = j + 1; k < ring.length; k++) {
        const set = [ring[i].hex, ring[j].hex, ring[k].hex];
        const r = validate(set, { mode: "light", surface: SURF, pairs: "all" });
        if (!r.ok) continue;
        const ps = [pair(set[0], set[1]), pair(set[0], set[2]), pair(set[1], set[2])];
        const cvd = Math.min(...ps.map(p => p.cvd));
        const norm = Math.min(...ps.map(p => p.normal));
        if (cvd < 8.0) continue;            // the dataviz CVD TARGET, not the floor band
        let chrome = 99;
        for (const s of set) for (const o of CHROME) chrome = Math.min(chrome, pair(s, o).normal);
        if (chrome < 15.0) continue;        // FOCAL / SHARED_FRONTIER are on the SAME screen
        let ext = 99;
        for (const s of set) for (const o of OA.concat(SDG)) ext = Math.min(ext, pair(s, o).normal);
        best.push({ L, set, cvd, norm, ext, chrome });
      }
}
best.sort((a, b) => (b.ext - a.ext) || (b.cvd - a.cvd));
console.log(`triples passing validator + cvd>=8 + chrome>=15: ${best.length}`);
for (const b of best.slice(0, 20))
  console.log(`  L ${b.L.toFixed(2)}  ${b.set.join(",")}  cvd ${b.cvd.toFixed(1)}  normal ${b.norm.toFixed(1)}  minExt ${b.ext.toFixed(1)}  minChrome ${b.chrome.toFixed(1)}`);
