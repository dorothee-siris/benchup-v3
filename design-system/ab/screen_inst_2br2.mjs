// Stream VS3 (Phase 2B-R2): the L = 0.77 institution trio + its darker same-hue
// twins, plus the full coexistence-distance matrix the A1 amendment asks to be
// RECORDED (institution fills vs OA / SDG / ERC / chrome). Throwaway screening
// tool, design-system/ab/** only -- the shipped evidence is the validator log in
// design-system/palette_validation.txt.
//
// Usage (cwd app/):
//   node design-system/ab/screen_inst_2br2.mjs "#FC9095,#28CFB7,#90B3FC"
import { validate, contrast } from "file:///C:/Users/theod/AppData/Local/Temp/claude/bundled-skills/2.1.251/06f447984e7673a25ccfaa2ab5a9cf1e/dataviz/scripts/validate_palette.js";

const SURF = "#FFFFFF";
const num = s => { const m = /ΔE ([0-9.]+)/.exec(s); return m ? +m[1] : NaN; };
function pair(a, b) {
  const r = validate([a, b], { mode: "light", surface: SURF, pairs: "all" });
  const rows = Object.fromEntries(r.report.map(x => [x[0], x[2]]));
  return { normal: num(rows["Normal-vision floor"]), cvd: num(rows["CVD separation"]) };
}

// --- OKLab <-> sRGB, the validator's own math (copied, not imported: the module
// exports validate/contrast only) --------------------------------------------
const s2lin = c => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
const lin2s = c => { c = Math.max(0, Math.min(1, c)); return c <= 0.0031308 ? 12.92 * c : 1.055 * c ** (1 / 2.4) - 0.055; };
const hex2srgb = h => { h = h.trim().replace(/^#/, ""); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255); };
function oklabFromLin([r, g, b]) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
          1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
          0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
}
const oklab = h => oklabFromLin(hex2srgb(h).map(s2lin));
function oklch(h) { const [L, a, b] = oklab(h); return [L, Math.hypot(a, b), ((Math.atan2(b, a) * 180 / Math.PI) % 360 + 360) % 360]; }
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
function lchHex(L, C, H) {           // clamp chroma into gamut, keeping L and H
  let c = C;
  while (c > 0 && !inGamut(lchToLinear(L, c, H))) c -= 0.002;
  return toHex(lchToLinear(L, Math.max(c, 0), H));
}

// --- the app's other families (hard-coded here; palette.py is the source) -----
const OA = ["#0CA750", "#FFCB3A", "#8190FF", "#F85C32"];
const SDG = ["#E5243B", "#DDA63A", "#4C9F38", "#C5192D", "#FF3A21", "#26BDE2", "#FCC30B",
             "#A21942", "#FD6925", "#DD1367", "#FD9D24", "#BF8B2E", "#3F7E44", "#0A97D9",
             "#56C02B", "#00689D"];
const ERC_NEW = ["#D55E00", "#009E73", "#6A3D9A"];
const CHROME = { FOCAL: "#0072B2", COMPARISON: "#8C9196", SHARED_FRONTIER: "#C2185B" };
const DOCTYPE = ["#22A2BD", "#A55F8F", "#667900", "#7838B6", "#A10A4E"];

const fills = (process.argv[2] || "#FC9095,#28CFB7,#90B3FC").split(",");

console.log("=== fills: OKLCH + contrast ===");
for (const f of fills) {
  const [L, C, H] = oklch(f);
  console.log(`  ${f}  L ${L.toFixed(3)}  C ${C.toFixed(3)}  H ${H.toFixed(1)}  contrast ${contrast(f, SURF).toFixed(2)}:1`);
}

console.log("=== pairwise inside the trio (normal / worst-CVD) ===");
let wn = 99, wc = 99;
for (let i = 0; i < fills.length; i++) for (let j = i + 1; j < fills.length; j++) {
  const p = pair(fills[i], fills[j]);
  console.log(`  ${fills[i]} <-> ${fills[j]}   normal ${p.normal.toFixed(1)}   cvd ${p.cvd.toFixed(1)}`);
  wn = Math.min(wn, p.normal); wc = Math.min(wc, p.cvd);
}
console.log(`  worst normal ${wn.toFixed(1)} | worst cvd ${wc.toFixed(1)}`);

console.log("=== coexistence distances (min over the family), RECORDED not required ===");
const fams = { OA, SDG, ERC: ERC_NEW, DOCTYPE, FOCAL: [CHROME.FOCAL], COMPARISON: [CHROME.COMPARISON], SHARED: [CHROME.SHARED_FRONTIER] };
for (const [name, fam] of Object.entries(fams)) {
  let mn = 99, mc = 99, arg = "";
  for (const f of fills) for (const g of fam) {
    const p = pair(f, g);
    if (p.normal < mn) { mn = p.normal; arg = `${f}<->${g}`; }
    mc = Math.min(mc, p.cvd);
  }
  console.log(`  vs ${name.padEnd(11)} min normal ${mn.toFixed(1)}  min cvd ${mc.toFixed(1)}   (${arg})`);
}

console.log("=== darker same-hue twins: first L (step .005 down) clearing 4.5:1 on white ===");
const twins = [];
for (const f of fills) {
  const [L0, C0, H] = oklch(f);
  let chosen = null;
  for (let L = L0; L > 0.2; L -= 0.005) {
    const cand = lchHex(L, C0, H);
    if (contrast(cand, SURF) >= 4.5) { chosen = { L, hex: cand }; break; }
  }
  const p = pair(f, chosen.hex);
  const [tl, tc, th] = oklch(chosen.hex);
  twins.push(chosen.hex);
  console.log(`  ${f} -> ${chosen.hex}  L ${tl.toFixed(3)} C ${tc.toFixed(3)} H ${th.toFixed(1)}  ` +
              `contrast ${contrast(chosen.hex, SURF).toFixed(2)}:1  dHue ${Math.abs(th - H).toFixed(1)}  ` +
              `normal-dE(fill,twin) ${p.normal.toFixed(1)}`);
}
console.log(`  twins: ${twins.join(",")}`);
console.log("=== twins pairwise (they appear together as legend text) ===");
for (let i = 0; i < twins.length; i++) for (let j = i + 1; j < twins.length; j++) {
  const p = pair(twins[i], twins[j]);
  console.log(`  ${twins[i]} <-> ${twins[j]}   normal ${p.normal.toFixed(1)}   cvd ${p.cvd.toFixed(1)}`);
}
