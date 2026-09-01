#!/usr/bin/env python3
"""
app/ops/trim_pair_topics.py -- BUILD_PLAN_2C.md Stream MT, D11 (Gate-2B-R3 ruling 5 /
grill Q10: "attempt Community Cloud as-is; trim collab_pair_topics top-100->top-50 ONLY
on deploy failure/platform pushback -- the trim script ships ready either way").

Trims the shipped `collab_pair_topics.parquet` (top-100 topics/pair by joint volume, see
pipeline/15_collab_pass.py::write_p7_topics / TOP_N_TOPICS_P7 = 100) down to the top-N
topics per pair -- the SAME ranking rule the pipeline itself uses (sort by
(a, b, vol desc), cumcount within group, keep rank < N) -- applied here to the
ALREADY-BUILT top-100 file instead of rerunning the full pipeline stage (no corpus
re-read, no checkpoint machinery needed; this is a pure re-filter of an existing table).

Default: do NOT run this. Ship the 21-file / ~273 MB deploy as-is (D11, ruled). Run this
ONLY if Streamlit Community Cloud actually rejects that size at push/build time.

Caveat (disclosed, not hidden): ties in `vol` sitting exactly on the Nth-place cutoff are
broken by the shipped file's own row order (a, b, topic_id ascending -- the order
write_p7_topics() re-sorted to for storage), not by whatever order the original pipeline
run held before ITS top-100 cut. This can only change which topic of an exact tie is kept
for a pair that has 2+ topics tied on `vol` straddling the cutoff -- the ranking itself
(which volumes qualify for the top N) is unaffected and correct either way.

Never overwrites the source file in place: always writes `<stem>_top<N>.parquet` next to
it. Swapping the trimmed file in for the full one -- point docs/data_contract.yaml's
collab_pair_topics.parquet entry at the new filename (row/column schema is IDENTICAL, so
no other contract field changes), then re-run `ops/deploy.py --check-only` -- is a
documented MANUAL step for whoever runs this; this script never touches
data_contract.yaml or app/data/ itself.

USAGE
  python ops/trim_pair_topics.py --dry-run                  # top-50 (the D11 rung), no write
  python ops/trim_pair_topics.py --dry-run --top-n 30        # size a different N
  python ops/trim_pair_topics.py                             # writes collab_pair_topics_top50.parquet
  python ops/trim_pair_topics.py --top-n 30                  # writes collab_pair_topics_top30.parquet
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1252 console -- top-of-script rule
except AttributeError:  # pragma: no cover
    pass

import pandas as pd

APP_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SRC = APP_DIR / "data" / "collab_pair_topics.parquet"


def log(msg: str) -> None:
    print(f"[trim_pair_topics] {msg}", flush=True)


def trim(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Re-rank each (a, b) group by vol descending, keep rank < top_n. Same rule as
    pipeline/15_collab_pass.py::write_p7_topics, applied to an already-capped-at-100 frame.
    observed=True everywhere -- a/b are category dtypes with ~55M possible (a, b) label
    combinations; without it groupby would materialize the full Cartesian product instead
    of just the ~a-few-million pairs that actually have rows."""
    d = df.sort_values(["a", "b", "vol"], ascending=[True, True, False])
    d["_rank"] = d.groupby(["a", "b"], observed=True).cumcount()
    d = d[d["_rank"] < top_n].drop(columns=["_rank"])
    return d.sort_values(["a", "b", "topic_id"]).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(DEFAULT_SRC),
                     help="collab_pair_topics.parquet to trim (default: app/data/collab_pair_topics.parquet)")
    ap.add_argument("--top-n", type=int, default=50, help="topics/pair to keep (default: 50, the D11 rung)")
    ap.add_argument("--dry-run", action="store_true", help="print projected row count + file size, write nothing")
    args = ap.parse_args()

    src = Path(args.source)
    if not src.is_file():
        log(f"ERROR: source not found: {src}")
        return 1

    src_mb = src.stat().st_size / (1024 * 1024)
    log(f"reading {src} ({src_mb:.2f} MB)...")
    df = pd.read_parquet(src)
    n_before = len(df)
    sizes = df.groupby(["a", "b"], observed=True).size()
    n_pairs = len(sizes)
    log(f"source: {n_before:,} rows, {n_pairs:,} distinct pairs with >=1 topic row, "
        f"max {int(sizes.max())} topics/pair")

    trimmed = trim(df, args.top_n)
    n_after = len(trimmed)
    n_affected_pairs = int((sizes > args.top_n).sum())
    pct_dropped = 100 * (n_before - n_after) / n_before if n_before else 0.0
    log(f"trimmed to top-{args.top_n}: {n_after:,} rows ({n_before - n_after:,} dropped, "
        f"{pct_dropped:.1f}%); {n_affected_pairs:,} of {n_pairs:,} pairs "
        f"({100 * n_affected_pairs / n_pairs:.2f}%) had more than {args.top_n} topics and lost rows")

    dest = src.with_name(f"{src.stem}_top{args.top_n}.parquet")

    if args.dry_run:
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            trimmed.to_parquet(tmp_path, index=False, compression="zstd")
            projected_mb = tmp_path.stat().st_size / (1024 * 1024)
        finally:
            tmp_path.unlink(missing_ok=True)
        log(f"DRY RUN -- projected {dest.name}: {n_after:,} rows, {projected_mb:.2f} MB "
            f"(source was {src_mb:.2f} MB, {projected_mb - src_mb:+.2f} MB delta) -- NOTHING WRITTEN")
        return 0

    if dest.exists():
        log(f"ERROR: {dest} already exists -- delete or rename it first (this script never overwrites).")
        return 1
    trimmed.to_parquet(dest, index=False, compression="zstd")
    dest_mb = dest.stat().st_size / (1024 * 1024)
    log(f"wrote {dest} -- {n_after:,} rows, {dest_mb:.2f} MB")
    log("MANUAL step required to actually use this file: point docs/data_contract.yaml's "
        f"collab_pair_topics.parquet entry at {dest.name} (schema is identical, only the "
        "row count changes), then re-run ops/deploy.py --check-only to confirm.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
