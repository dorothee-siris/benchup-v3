# BenchUp v3

A thematic benchmarking tool for European research institutions: find who resembles a
given institution across independent lenses, compare institutions side by side, and
explore collaboration patterns. Candidates for review, not a verdict.
Find ships in Phase 2A (this build); Compare and Collaborate are Phase 2B.

## Run

```
envs\env-app\Scripts\python.exe -m streamlit run Menu.py
```
(from this `app/` directory; the venv lives at `V3/envs/env-app`, one level up).

## Test

```
envs\env-app\Scripts\python.exe -m pytest tests -q
envs\env-app\Scripts\python.exe ops\_probe_menu.py
envs\env-app\Scripts\python.exe tests\ui\smoke.py --port 8611
```

## Layout

See `V3/BUILD_PLAN_2A.md` §2 ("Architecture & journeys") for the full repo layout, data
flow, and the per-stream file ownership map. `V3/config/config.yaml` (the `proposal_r5`
block) is the single source of every value in `config.yaml`; `app/config.yaml` is the
flat, ruling-id-commented copy this app actually reads.
