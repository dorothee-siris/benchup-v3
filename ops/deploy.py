"""ops/deploy.py -- validates the source tables against docs/data_contract.yaml, then copies
the contract's declared files into data/ (byte copies -- no re-serialization, so repeated runs
are byte-identical) and writes data/MANIFEST.json. Exits non-zero on ANY contract violation;
prints every table's verdict either way. Pattern adapted from the Lorraine Phase-2 Explorer's
pipeline/60_deploy.py (see app/docs/VENDORED.md).

Source layout (config-driven over contract["files"], not hardcoded per table):
  - the 8 *.parquet tables come from --source (default ../data/artefacts_eu, relative to app/)
  - overrides/type_overrides.csv comes from V3/data/overrides/type_overrides.csv (the Annuaire-
    pattern locked override list lives outside artefacts_eu, per BUILD_PLAN)
  - overrides/umbrella_supplement.csv is authored in place at app/data/overrides/ (this stream) --
    its own location IS the deploy target, so deploy is a validate-in-place no-op copy for this
    one file.

Usage:
  python ops/deploy.py [--source ../data/artefacts_eu] [--check-only]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from contract_check import check  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]  # app/


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_source(fname: str, source_dir: Path) -> Path:
    """Where a declared file lives BEFORE deploy. Config-driven over the two override files;
    every other declared file (the 8 parquet tables) is source_dir/fname."""
    if fname == "overrides/type_overrides.csv":
        return ROOT.parent / "data" / "overrides" / "type_overrides.csv"
    if fname == "overrides/umbrella_supplement.csv":
        return ROOT / "data" / "overrides" / "umbrella_supplement.csv"
    return source_dir / fname


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="../data/artefacts_eu",
                         help="directory the 8 parquet tables are read from (default: ../data/artefacts_eu)")
    parser.add_argument("--check-only", action="store_true", help="validate the source tables, do not copy/write MANIFEST")
    parser.add_argument("--contract", default=None, help="path to data_contract.yaml (default: docs/data_contract.yaml)")
    parser.add_argument("--out-dir", default=None, help="deploy target override (default: contract['deploy_target'], i.e. data/)")
    args = parser.parse_args()

    contract_path = Path(args.contract) if args.contract else ROOT / "docs" / "data_contract.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    source_dir = (ROOT / args.source).resolve() if not Path(args.source).is_absolute() else Path(args.source)
    out_dir = Path(args.out_dir) if args.out_dir else ROOT / contract["deploy_target"]

    print(f"contract      : {contract_path} (v{contract.get('contract_version')}, snapshot {contract.get('snapshot')})")
    print(f"source dir    : {source_dir}")
    print(f"deploy target : {out_dir}")
    print(f"mode          : {'CHECK-ONLY' if args.check_only else 'VALIDATE + DEPLOY'}")
    print()

    resolver = lambda fname: resolve_source(fname, source_dir)  # noqa: E731
    violations = check(source_dir, contract, resolve=resolver)

    # per-file verdict (same shape as contract_check's own CLI printout)
    by_file: dict[str, list[str]] = {fname: [] for fname in contract["files"]}
    for v in violations:
        by_file.setdefault(v.split(":", 1)[0], []).append(v)
    for fname in contract["files"]:
        vs = by_file.get(fname, [])
        src = resolve_source(fname, source_dir)
        if vs:
            print(f"--- {fname} (source: {src}): FAIL ({len(vs)}) ---")
            for v in vs:
                print(f"  ! {v}")
        else:
            print(f"--- {fname} (source: {src}): PASS ---")

    if violations:
        print(f"\nDEPLOY ABORTED -- {len(violations)} contract violation(s) found above.")
        return 1

    if args.check_only:
        print(f"\ncontract_check OK -- {len(contract['files'])} file(s) verified, nothing copied (--check-only)")
        return 0

    # copy every declared file into out_dir, preserving its declared relative path
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_files: dict[str, dict] = {}
    for fname in contract["files"]:
        src = resolve_source(fname, source_dir)
        dest = out_dir / fname
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        manifest_files[fname] = {
            "sha256": _sha256(dest),
            "n_rows": _n_rows(dest),
            "size_bytes": dest.stat().st_size,
        }
        print(f"  OK -> {dest} ({manifest_files[fname]['n_rows']:,} rows, {manifest_files[fname]['size_bytes']:,} bytes)")

    manifest = {
        "deployed_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": contract.get("snapshot"),
        "source_manifest_generated_at": contract.get("generated_at"),
        "contract_version": contract.get("contract_version"),
        "files": manifest_files,
        "type_overrides": {
            "sha256": manifest_files["overrides/type_overrides.csv"]["sha256"],
            "n_rows": manifest_files["overrides/type_overrides.csv"]["n_rows"],
        },
    }
    manifest_path = out_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nDEPLOY OK -- {len(contract['files'])} file(s) deployed; wrote {manifest_path}")
    return 0


def _n_rows(path: Path) -> int:
    if path.suffix == ".csv":
        import pandas as pd
        return len(pd.read_csv(path))
    import pyarrow.parquet as pq
    return pq.ParquetFile(path).metadata.num_rows


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:  # pragma: no cover
        pass
    sys.exit(main())
