# BenchUp v3

A thematic benchmarking tool for European research institutions: find who resembles a
given institution across independent lenses, compare institutions side by side, and
explore collaboration patterns. Candidates for review, not a verdict.

Four pages, in the order most readings take (2B-10):

1. **Find peers** -- start from one institution, see who resembles it lens by lens. Phase 2A.
2. **Compare** -- put a shortlist of 2-6 institutions side by side across the same lenses:
   subject profile, specialisations, ERC/SDG mirrors, frontier positioning, impact
   intervals, trends and coverage. Phase 2B.
3. **Collaborate** -- take one pair and read what they already share, what each lacks that
   the other holds, and where their publications meet on OpenAlex. Phase 2B.
4. **How it is built** (the Methods page) -- one section per objection a reader is entitled
   to raise, every figure filled in at run time from the same snapshot the other three
   pages read, plus a download of the same sections as a human-readable note
   (`docs/METHODS_NOTE.md`). Phase 2B.

`Menu.py` enumerates the four cards in that order and lights up each one only once its
page file exists under `pages/`, so it never breaks while a later page is still being
built.

This README covers two journeys: **developer** (clone this repo, get the app running,
run its tests) and **operator** (refresh the underlying data and redeploy). If you only
have this repo -- the public GitHub clone -- you have everything the developer journey
needs, data included. The operator journey needs the private SIRIS `V3/` project tree
this repo is a subfolder of; see [Pipeline refresh](#pipeline-refresh) for why.

## Clone

```powershell
git clone https://github.com/dorothee-siris/benchup-v3.git
cd benchup-v3
```
The clone already contains `data/` -- 21 parquet/csv/json files, ready to run. This repo
ships its own analytical data (see [Data](#data)); there is no separate data download step.

## Environment setup

Any Python 3.12 works; the pins below are what this app is verified against
(`requirements.txt`'s own header: "bump deliberately, re-run pytest + the Playwright probe").

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # only needed to run tests/smoke/probe, not to run the app
```
(SIRIS-internal convention: the venv lives one level **above** this repo, at `V3\envs\env-app`
-- hence every command below being written `..\envs\env-app\Scripts\python.exe` rather than
`.venv\Scripts\python.exe`. A public-repo clone will not have that sibling folder; create
your own venv wherever you like and adjust the path.)

## Data

`data/` is validated against `docs/data_contract.yaml` -- the one schema-authority file --
by `ops/deploy.py`. Check the data you have matches what the app expects:
```powershell
..\envs\env-app\Scripts\python.exe ops\deploy.py --check-only
```
As shipped: **21 files, 272.77 MB total**, every file strictly under the 95 MB GitHub
per-file cap (largest: `collab_pair_topics.parquet`, 62.62 MB). `--check-only` prints a
per-file size audit and validates every declared dtype/column/key -- it exits non-zero on
any mismatch, so a clean run is a real guarantee, not a spot check.

## Run

```powershell
cd "C:\Users\theod\SIRIS\Internal Projects\BenchUp\V3\app"
..\envs\env-app\Scripts\python.exe -m streamlit run Menu.py
```
Two things the command depends on:
- The venv lives at `V3/envs/env-app`, **one level up** from `app/` -- hence `..\envs\...`
  (SIRIS-internal path; see [Environment setup](#environment-setup) if you cloned the
  public repo standalone).
- In PowerShell the path must be quoted. Unquoted, the space in `Internal Projects` splits
  it into two arguments and `cd` fails with `PositionalParameterNotFound`.

## Test

```powershell
..\envs\env-app\Scripts\python.exe -m pytest tests -q
..\envs\env-app\Scripts\python.exe ops\_probe_menu.py
..\envs\env-app\Scripts\python.exe tests\ui\smoke.py --port 8611
..\envs\env-app\Scripts\python.exe tests\ui\probe.py all
```
Two disclosed flakes, both understood, neither a real regression -- do not chase either:
- **`tests/test_engine_identity.py::test_budgets`** (an RSS ceiling test) fails only inside
  a full `pytest tests -q` run, because it measures *cumulative* RSS across every test that
  ran before it in the same process; it passes in isolation
  (`..\envs\env-app\Scripts\python.exe -m pytest tests/test_engine_identity.py::test_budgets -q`).
- **`tests/ui/smoke.py`'s workbook-download check** times out on its own trigger-and-wait
  sequence inside the smoke harness specifically. `tests/ui/probe.py`'s more careful version
  of the same check passes and validates all 10 xlsx sheets -- treat a smoke run that is one
  short of its full count as green, not as a regression to chase, if the one failure is this
  check.

Exact pytest/smoke/probe counts move as work lands; run the commands above for the live
number rather than trusting a count typed into a doc -- multiple 2C streams are landing
concurrently as this README is written.

## Pipeline refresh

Refreshing the analytical data (a new OpenAlex snapshot, a taxonomy change, a new pipeline
step) is documented end to end in **`../pipeline/README.md`** -- steps 14 through 18, the
real execution order (**14 → 16 → 17 → 18 → 15**, not file-number order), credentials,
checkpoint/resume behavior, and a Windows-console encoding gotcha every pipeline script
needs to guard against.

**That link only resolves for a SIRIS operator with the full private `V3/` project tree.**
This repo (`app/`) is a subfolder of `V3/`; `pipeline/`, `data/raw/`, `data/interim/` and
`data/artefacts_eu/` all live one level up and are **not** part of this public GitHub repo
-- a clone of `dorothee-siris/benchup-v3` gets the app and its already-baked data, never
the pipeline that produced it. If you only have this repo, the pipeline runbook is not
reachable from here; that is by design, not a broken link to fix.

## Deploy

Public Streamlit Community Cloud app, built from this repo
(`github.com/dorothee-siris/benchup-v3`). The push to `main` is the one human-gated step;
Community Cloud then builds directly from the repo's `data/` (already-baked, per
[Data](#data)) -- there is no separate data upload. Before pushing a data refresh, always
run `ops/deploy.py --check-only` (see [Data](#data)) so a contract violation is caught here,
not on the deploy platform.

If Community Cloud rejects the current ~273 MB total: `pipeline/README.md`'s
[trim ladder](../pipeline/README.md#trim-ladder-d11) documents a ranked set of further cuts,
measured (not guessed) but **none executed** -- `ops/trim_pair_topics.py --dry-run` sizes
the first rung on demand.

## Repo hygiene

### `_TO_DELETE_20260831/` -- disposition (never deleted by this stream; user sign-off pending)

Contents (4 files, all currently tracked in git):
```
_TO_DELETE_20260831/nul_stray_artifact          (0 bytes -- a stray file from an earlier
                                                  Windows-shell redirect typo, e.g. `> nul`
                                                  in a shell that does not treat `nul` as a
                                                  null device the way cmd.exe does)
_TO_DELETE_20260831/ops/_probe_collab.py        (27,975 bytes)
_TO_DELETE_20260831/ops/_probe_compare.py       (37,143 bytes)
_TO_DELETE_20260831/ops/_probe_find.py          (22,239 bytes)
```
The three `_probe_*.py` files are the pre-2B-R3 per-view Playwright probes, superseded by
`tests/ui/probe.py` (one parameterised file covering all three views, per
`progress/2BR3_TEVU.md`'s own "359->259 checks, one parameterised probe (80 checks) replaces
three" note).

**Reference sweep** (`grep -rln` for each of the three basenames plus `nul_stray_artifact`,
across every tracked file type in this repo):

| File | Live code references | What the hits actually are |
|---|---|---|
| `nul_stray_artifact` | **0** | Nothing anywhere references it. |
| `ops/_probe_collab.py` | **0** live imports | 1 hit: `lib/copy.py:1564`, a comment reading *"ONE caller (`ops/_probe_collab.py`, itself deleted this wave, superseded by..."* -- a historical note, not a dependency. |
| `ops/_probe_compare.py` | **0** live imports | Mentioned only inside `tests/ui/probe.py`'s own docstring/comments (lines 4, 314, 465, 569) as *"Ported/rewritten from ops/_probe_compare.py"* / *"(all now DELETED, superseded by this file)"*, and in `tests/ui/README.md:38` (*"...all DELETED"*). |
| `ops/_probe_find.py` | **0** live imports | Same pattern: `lib/views_find.py:1701` (a comment naming the old file for context), `design-system/CHROME_CONTRACT.md:6` (a stale companion-doc filename reference, itself pre-dating this file's move), `tests/ui/probe.py` and `tests/ui/README.md` (same "ported from / all DELETED" notes as above). |

Every single hit is a **comment or docstring explicitly stating the file is already
deleted/superseded** -- none is a live `import` or a runtime path reference. `tests/ui/probe.py`
defines its own same-named functions (`_probe_find`, `_probe_compare`, `_probe_collab`,
lines 233/327/478) as their replacement; it does not import from the old files. (Two stale
compiled artifacts also exist at `ops/__pycache__/_probe_collab.cpython-312.pyc` and
`_probe_find.cpython-312.pyc` -- leftover bytecode cache from when these scripts lived
directly under `ops/`, before their move into `_TO_DELETE_20260831/ops/`; `__pycache__/` is
gitignored and harmless, not evidence of a live reference.)

**Recommendation:** every file in `_TO_DELETE_20260831/` is safe to delete on the numbers
above -- zero live references found by an exhaustive grep sweep, every mention elsewhere in
the codebase is a comment already saying "deleted." The one thing worth knowing before
deleting: **all four files are currently tracked in git** (`git ls-files` confirms), so
removing them needs `git rm` (or an equivalent commit), not just a filesystem delete, or
they will reappear on the next `git status`/`git checkout`. This stream does not delete or
move anything -- the standing "never delete" rule applies to agents; this table is the
evidence for whoever signs off on the deletion.

### `.gitignore` audit

Swept `git ls-files` against the obvious offenders: `.env`/secrets, `*.log`, `__pycache__/`,
`.pyc`, any checkpoint/interim/raw data directory, `.pytest_cache/`. **Zero violations
found** -- nothing raw, interim, or secret is tracked that should not be. (`data/` itself
is 21 contract files + 3 override CSVs, all intentionally tracked -- see [Data](#data); this
repo ships its own baked data by design, that is not a leak.)

Added four defensive entries that were simply never needed until now (nothing currently on
disk violates them -- this closes a gap the audit exposed, not a fix to an existing
problem):
```
*.log
*.tmp
.vscode/
.idea/
Thumbs.db
.DS_Store
```
`_TO_DELETE_20260831/` (and any future `_TO_DELETE_*` folder) is deliberately **not**
gitignored -- the entire point of that convention is for the folder to stay visible for
review until someone signs off on deleting it; hiding it from git would defeat that.

## Layout

See `V3/BUILD_PLAN_2A.md` §2 ("Architecture & journeys") for the full repo layout, data
flow, and the per-stream file ownership map. `V3/config/config.yaml` (the `proposal_r5`
block) is the single source of every value in `config.yaml`; `app/config.yaml` is the
flat, ruling-id-commented copy this app actually reads. `../pipeline/README.md` documents
how the data in `data/` was produced (SIRIS-internal only, see
[Pipeline refresh](#pipeline-refresh) above).
