# ChartGen

Streamlit desktop application. Pulls benchmarking data from two NHS toolkit APIs, normalises it into canonical data shapes, and generates PowerPoint and PDF reports from a user-authored Running Order against a marked-up template.

One user, one machine, one workfile at a time. Workfiles are shared through SharePoint via OneDrive sync.

## Run

```
run_chartgen.bat
```

Creates the venv from `requirements.txt` on first run, then `streamlit run app.py`. To add a dependency: add it to `requirements.txt`, delete `venv/`, relaunch.

`requirements.txt` is pinned to exact versions, so a rebuild reproduces what currently works rather than whatever is newest on PyPI that day. Upgrading is a deliberate act: change the pin, delete `venv/`, relaunch, and check the outputs. Matplotlib is the one to watch, since a new version can change default spacing or fonts and so alter every chart without any change to this codebase.

## Tests

```
run_tests.bat
```

Roughly 340 checks, a few seconds. Same venv, plus `requirements-dev.txt`, which is separate from `requirements.txt` on purpose: that one builds every colleague's application venv and ships in the installer.

The suite covers the pure logic and the round trips, not the interface. A green run means logic that used to be right still is. It says nothing about whether a chart looks right, and it never replaces running the application. Selection rule, coverage and the deliberate boundaries are in `tests/CLAUDE.md`.

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

## Known gaps

Deliberate or accepted, not oversights to fix in passing. Raise before acting on any of them.

**Most of the application is not covered by tests, on purpose.** The Streamlit UI, the PowerPoint and Excel COM automation, chart appearance and the toolkit APIs are all excluded, with reasons, in `tests/CLAUDE.md`. That is a large share of the codebase, so never present a green test run as evidence that a change works. Anything visual, anything touching Office, and anything user-facing still has to be seen in the running application.

**Two unused definitions, both left on purpose.** `has_valid_unit_data` on the data shapes, to be revisited when the tool is mature if still unused. `_apply_spine_style` in `base_charts/categorical_compositional/yn_bar.py`, left because these files are handed whole to an external AI and pasted back, so an edit there is lost the next time that happens.

## Documentation

`docs/` holds reference material: data formats, glossary, features, architecture overview. Operative rules live in `CLAUDE.md` files next to the code they govern, not in `docs/`.
