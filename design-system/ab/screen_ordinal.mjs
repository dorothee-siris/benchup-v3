import { validateOrdinal, contrast } from "file:///C:/Users/theod/AppData/Local/Temp/claude/bundled-skills/2.1.250/7d34fd5c5ca02f9d932830007398ac3e/dataviz/scripts/validate_palette.js";
for (const arg of process.argv.slice(2)) {
  const set = arg.split(",");
  const r = validateOrdinal(set, { mode: "light", surface: "#FFFFFF" });
  console.log("=== " + arg + "  -> " + (r.ok ? "OK" : "NOT OK"));
  for (const row of r.report) console.log("   ", row[0], "|", row[1], "|", row[2]);
  console.log("    contrasts: " + set.map(c => c + " " + contrast(c, "#FFFFFF").toFixed(2)).join("  "));
}
