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

## Run

```powershell
cd "C:\Users\theod\SIRIS\Internal Projects\BenchUp\V3\app"
..\envs\env-app\Scripts\python.exe -m streamlit run Menu.py
```

Two things the command depends on:
- The venv lives at `V3/envs/env-app`, **one level up** from `app/` — hence `..\envs\...`.
- In PowerShell the path must be quoted. Unquoted, the space in `Internal Projects` splits
  it into two arguments and `cd` fails with `PositionalParameterNotFound`.

## Test

```
..\envs\env-app\Scripts\python.exe -m pytest tests -q
..\envs\env-app\Scripts\python.exe ops\_probe_menu.py
..\envs\env-app\Scripts\python.exe tests\ui\smoke.py --port 8611
```

## Layout

See `V3/BUILD_PLAN_2A.md` §2 ("Architecture & journeys") for the full repo layout, data
flow, and the per-stream file ownership map. `V3/config/config.yaml` (the `proposal_r5`
block) is the single source of every value in `config.yaml`; `app/config.yaml` is the
flat, ruling-id-commented copy this app actually reads.
