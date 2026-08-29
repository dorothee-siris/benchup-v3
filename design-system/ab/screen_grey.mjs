import { validate, contrast } from "file:///C:/Users/theod/AppData/Local/Temp/claude/bundled-skills/2.1.250/7d34fd5c5ca02f9d932830007398ac3e/dataviz/scripts/validate_palette.js";
const SURF = "#FFFFFF";
const num = s => { const m = /ΔE ([0-9.]+)/.exec(s); return m ? +m[1] : NaN; };
const set = process.argv[2].split(",");
const r = validate(set, { mode: "light", surface: SURF, pairs: "adjacent" });
for (const row of r.report) console.log(" ", row.join(" | "));
console.log("adjacent-step normal-vision distance + contrast + lightness:");
for (let i = 0; i < set.length; i++) {
  let d = "";
  if (i) {
    const p = validate([set[i - 1], set[i]], { mode: "light", surface: SURF, pairs: "all" });
    const rows = Object.fromEntries(p.report.map(x => [x[0], x[2]]));
    d = `stepNormal ${num(rows["Normal-vision floor"]).toFixed(1)}`;
  }
  console.log(`  ${set[i]}  contrast ${contrast(set[i], SURF).toFixed(2)}  ${d}`);
}
