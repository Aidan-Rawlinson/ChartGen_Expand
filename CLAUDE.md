# ChartGen

Streamlit desktop application. Pulls benchmarking data from two NHS toolkit APIs, normalises it into canonical data shapes, and generates PowerPoint and PDF reports from a user-authored Running Order against a marked-up template.

One user, one machine, one workfile at a time. Workfiles are shared through SharePoint via OneDrive sync.

## Run

```
run_chartgen.bat
```

Creates the venv from `requirements.txt` on first run, then `streamlit run app.py`. To add a dependency: add it to `requirements.txt`, delete `venv/`, relaunch.

There are no tests. Verification is by running the application.

## Layout

| Package | Owns |
|---|---|
| `chartgen/session_shell/` | Sign-in, the advisory workfile lock, startup file association, update check |
| `chartgen/workfile/` | The `.cgw` format and the in-session `WorkfileState` |
| `chartgen/acquisition/` | Two toolkit APIs, template reading, the manifest table |
| `chartgen/output_generation/definition/` | The Running Order: schema, generation, row operations, xlsx round-trip |
| `chartgen/output_generation/execution/` | Running a Running Order: dispatch, rendering, PowerPoint output |
| `chartgen/shared/` | Canonical data shapes, population resolution, and generic infrastructure |
| `chartgen/ui/` | Streamlit only |

Layer order is `ui` above `output_generation` above `acquisition` above `shared`. Imports go one way only. `shared` imports from nothing above it.

## Standing rules

**Fail visibly.** No silent clamps, no dropping on mismatch, no fallback defaults. If something is wrong, it stops or it is reported.

**Validate only where designed.** Input validation and defensive guards are an architectural decision, not a local fix. Raise it before adding one. A guard added while fixing something else usually signals a problem upstream that the guard does not fix.

**Stored values are never rewritten.** A value the user picked or typed stays exactly as they left it. Nothing re-derives, reconstructs or normalises it on a later pass.

**Base Charts and Base Tables are outside the system boundary.** Standalone rendering artefacts, one file each, no shared helpers, no imports from ChartGen. Do not refactor, deduplicate or extract common code from them, however much they repeat. See `output_generation/execution/charts/base_charts/CLAUDE.md`.

**Design before build.** Agree the approach before writing the code.

## Documentation

`docs/` holds reference material: data formats, glossary, features, architecture overview. Operative rules live in `CLAUDE.md` files next to the code they govern, not in `docs/`.
