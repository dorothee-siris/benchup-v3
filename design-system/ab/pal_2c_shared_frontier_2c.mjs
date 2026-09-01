// PAL, Phase 2C (D7 ratified): full-pass validation of the NEW SHARED_FRONTIER
// hex #821D13 (replaces #7A1600) against EVERY hue it can appear beside on a
// screen -- vermillion, the navy institution trio, JOINT_COLOR, SDG cyan,
// momentum grey, all four OA domains, all three ERC domains, FOCAL and
// COMPARISON. Self-contained (no external import, same reason WT's claim-5
// scripts are self-contained: the bundled-skills validator path is
// session-specific) -- OKLab-Euclidean "Delta E" + Machado/Oliveira/Fernandes
// 2009 deutan simulation, IDENTICAL formulas to
// evals/wind_tunnel_2C/wt_claim5_frontier_red.mjs and
// evals/wind_tunnel_2BR3/wt_task2_pal_remeasure.mjs, so results are directly
// comparable to every number already recorded in lib/palette.py and
// palette_validation.txt.
//
// WHY A NEW SCRIPT RATHER THAN RE-RUNNING WT'S: WT's
// wt_claim5_frontier_red.mjs CANDIDATES dict was edited iteratively during the
// wind-tunnel session and the copy left on disk no longer contains the exact
// three hexes (#821D13 / #801D06 / #82182E) tabulated in WT_2C.md claim 5 --
// only the earlier cand_A/B/C exploration is still there. This script is PAL's
// own re-derivation, run against the LITERAL ratified hex (not regenerated
// from OKLCH, so there is no rounding daylight between "what the formula
// says" and "what lib/palette.py ships"), kept under design-system/ab/ (PAL's
// owned path) so it is re-runnable by any future editor with plain `node`.
//
// Run: node design-system/ab/pal_2c_shared_frontier_2c.mjs

const hex2srgb = (h) => { h = h.trim().replace(/^#/, ""); return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255); };
const s2lin = (c) => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
const lin = (h) => hex2srgb(h).map(s2lin);
function oklabFromLin([r, g, b]) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553*l+0.7936177850*m-0.0040720468*s, 1.9779984951*l-2.4285922050*m+0.4505937099*s, 0.0259040371*l+0.7827717662*m-0.8086757660*s];
}
function oklchOf(h) {
  const [L, a, b] = oklabFromLin(lin(h));
  const C = Math.hypot(a, b);
  let H = Math.atan2(b, a) * 180 / Math.PI;
  if (H < 0) H += 360;
  return [L, C, H];
}
const oklab = (h) => oklabFromLin(lin(h));
function deltaE(h1, h2) { const a = oklab(h1), b = oklab(h2); return 100 * Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]); }

const DEUTAN = [[0.367322, 0.860646, -0.227968],[0.280085, 0.672501, 0.047413],[-0.011820, 0.042940, 0.968881]];
function simulateDeutan(h) {
  const [r, g, b] = lin(h);
  const clamp = (c) => Math.max(0, Math.min(1, c));
  return [clamp(DEUTAN[0][0]*r+DEUTAN[0][1]*g+DEUTAN[0][2]*b), clamp(DEUTAN[1][0]*r+DEUTAN[1][1]*g+DEUTAN[1][2]*b), clamp(DEUTAN[2][0]*r+DEUTAN[2][1]*g+DEUTAN[2][2]*b)];
}
function deltaEDeutan(h1, h2) { const a = oklabFromLin(simulateDeutan(h1)), b = oklabFromLin(simulateDeutan(h2)); return 100 * Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]); }

function relLum(h) { const [r,g,b] = lin(h); return 0.2126*r + 0.7152*g + 0.0722*b; }
function contrast(h1, h2) { const L1 = relLum(h1)+0.05, L2 = relLum(h2)+0.05; return L1 > L2 ? L1/L2 : L2/L1; }

const NEW_RED = "#821D13";
const OLD_RED = "#7A1600";
const VERMILLION = "#D55E00";
const NAVY = ["#192C41", "#5A6883", "#B5C0D4"];
const JOINT_COLOR = "#2F3B52";
const SDG_CYAN = "#26BDE2";       // SDG-6 Clean Water and Sanitation
const MOMENTUM_GREY = "#727272";  // momentum "stable"
const OA = { Life: "#0CA750", Social: "#FFCB3A", Physical: "#8190FF", Health: "#F85C32" };
const ERC = { PE: "#6A3D9A", LS: "#009E73", SH: "#D55E00" };
const FOCAL = "#0072B2";
const COMPARISON = "#8C9196";

const FLOOR = 15; // the floor every cross-family / navy-adjacent pair in this file is held to (runs 14-16)

const [L, C, H] = oklchOf(NEW_RED);
console.log(`SHARED_FRONTIER NEW #821D13 in OKLCH: L=${L.toFixed(4)} C=${C.toFixed(4)} H=${H.toFixed(1)} deg`);
console.log(`(old #7A1600 was L=${oklchOf(OLD_RED)[0].toFixed(4)} C=${oklchOf(OLD_RED)[1].toFixed(4)} H=${oklchOf(OLD_RED)[2].toFixed(1)} deg)`);

function row(label, hex) {
  const dN = deltaE(NEW_RED, hex), dD = deltaEDeutan(NEW_RED, hex);
  const verdict = (dN >= FLOOR && dD >= FLOOR) ? "PASS" : "FAIL";
  console.log(`  vs ${label.padEnd(22)} ${hex}: normal ${dN.toFixed(2).padStart(6)}  deutan ${dD.toFixed(2).padStart(6)}  -> ${verdict}`);
  return dN >= FLOOR && dD >= FLOOR;
}

console.log(`\n=== SHARED_FRONTIER #821D13 vs every hue it can share a screen with (floor >=${FLOOR} normal AND deutan) ===`);
let allPass = true;
allPass &= row("vermillion (ERC-SH/momentum-down)", VERMILLION);
NAVY.forEach((n, i) => { allPass &= row(`navy slot ${i+1} (institution)`, n); });
allPass &= row("JOINT_COLOR (Collaborate pulse)", JOINT_COLOR);
allPass &= row("SDG-6 cyan (label accent)", SDG_CYAN);
allPass &= row("momentum grey 'stable'", MOMENTUM_GREY);
for (const [name, hex] of Object.entries(OA)) allPass &= row(`OA ${name}`, hex);
for (const [name, hex] of Object.entries(ERC)) allPass &= row(`ERC ${name} (label accent)`, hex);
allPass &= row("FOCAL", FOCAL);
allPass &= row("COMPARISON", COMPARISON);

console.log(`\n=== contrast vs white #FFFFFF (bars/bubbles must read; floor ~3:1 for a filled mark) ===`);
console.log(`  NEW #821D13: ${contrast(NEW_RED, "#FFFFFF").toFixed(2)}:1`);
console.log(`  OLD #7A1600: ${contrast(OLD_RED, "#FFFFFF").toFixed(2)}:1  (for comparison)`);

console.log(`\n=== contrast vs navy dots specifically (the user's original complaint) ===`);
NAVY.forEach((n, i) => {
  console.log(`  NEW vs slot ${i+1} ${n}: ${contrast(NEW_RED, n).toFixed(2)}:1   OLD vs slot ${i+1}: ${contrast(OLD_RED, n).toFixed(2)}:1`);
});

console.log(`\n=== OVERALL: ${allPass ? "ALL CHECKS PASS" : "SOME CHECKS FAILED"} ===`);
