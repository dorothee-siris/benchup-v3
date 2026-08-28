"""Test bootstrap: put `app/` on sys.path and point BENCHUP_V3_ROOT at the V3
folder that contains it (only used to reach the optional multi-tree golden
parquet under `data/artefacts_eu/eval_golden/`). Nothing else belongs here."""
import os
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
os.environ.setdefault("BENCHUP_V3_ROOT", str(APP_ROOT.parent))
