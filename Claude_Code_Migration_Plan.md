# ChartGen - Claude Code Migration Plan

Execution plan. Stages run in order.

---

## Scope

Change only: markdown files, docstrings, comments, file locations, import paths arising from a move.

No change to the function of code without explicit permission. Defects found in passing are raised, not fixed.

Every new document is reviewed and approved before it becomes authoritative. Produce one document at a time.

**Stop rule.** One stage per session. Stop at each stage boundary and wait for approval before starting the next. Do not read ahead and begin later stages.

**Lead surface** is marked per stage. Approval and review always sit with Aidan regardless of surface.

---

## Stage 1 - Restructure

*Lead: Claude Code*

Target layout:

```
ChartGen_Expand/            (repo root)
├── CLAUDE.md
├── README.md
├── requirements.txt
├── run_chartgen.bat
├── app.py
├── .streamlit/
├── docs/
├── installer/
├── user_resources/
├── chartgen/               (was core/)
│   ├── acquisition/
│   ├── output_generation/
│   ├── session_shell/
│   ├── shared/
│   ├── ui/
│   └── workfile/
└── venv/                   (gitignored)
```

Agreed changes:

1. Rename `core/` to `chartgen/`. Update every import across the codebase.
2. Remove the `code_base/` and `ChartGen/` container folders. Repo root becomes project root.
3. Move `installer/` to repo root.
4. Move `venv/` to repo root. Requires a path change in `run_chartgen.bat` - behavioural, permission granted for this change only.
5. Repoint `run_chartgen.bat` to install from `requirements.txt` instead of its hardcoded package list. Reconcile `requirements.txt` against the hardcoded list first and confirm the result before repointing - `requirements.txt` has never been read and may be stale. Behavioural, permission granted for this change only.

Not changing: the `.bat` installs only when no venv exists. Adding a dependency still means deleting the venv and relaunching.

Rejected: `src/` layout - solves an import-ambiguity problem that does not apply, since ChartGen is never pip-installed.

Deferred: `pyproject.toml` - touches launcher and installer, serves nothing in this migration.

Stage 1 outcome:
- Item 4 was a no-op. `venv/`, `app.py` and `run_chartgen.bat` were already siblings inside the old container, so flattening moved them to the root together and `cd /d "%~dp0"` still resolves. No `run_chartgen.bat` path change was needed; that permission went unused.
- Item 5 reconciliation: `requirements.txt` was identical to the hardcoded list - same 10 packages, same order. Clean swap.
- `venv/` was deleted rather than moved. A moved Windows venv breaks: `activate.bat` hardcodes an absolute `VIRTUAL_ENV` and prepends it to `PATH`. Rebuilt from `requirements.txt` via the repointed launcher path.
- Rename surface: 91 files edited. 306 import lines plus docstring and comment path references. `installer/ChartGen.iss` and `user_resources/Installer_Guide.md` also repointed.

Raised, not fixed:
- No `tests/` anywhere in the tree.
- No version pins anywhere. `requirements.txt` names 10 packages with no constraints, so every venv rebuild resolves to whatever is current on PyPI. The rebuild in this stage may have installed different versions than the venv it replaced.
- `installer/Output/ChartGen.zip` and `installer/Output/ChartGen_Setup.exe` are tracked in Git, against the stated intent in `ChartGen.iss` that the compiled artefact is never stored there. The `.gitignore` pattern `installer/Output/` is root-anchored and never matched the old nested path. It matches now, but Git keeps tracking files already tracked, so the binaries stay versioned until explicitly untracked.
- `static_docs_mirror/` and `dynamic_docs/` still carry `core/` path references (63 and 31 lines). Left untouched: the former is Stage 2's source and Stage 2 verifies facts against the codebase, the latter is deleted at the end of Stage 2.

**Final step of this stage:** update the paths in this plan file to match the new layout.

Commit before Stage 2 begins.

---

## Stage 2 - Documents

*Lead: Claude Code - facts must be verified against the codebase, not carried over from the source documents*

Produce in this order, one at a time, each approved before the next:

| Output | Source |
|---|---|
| `docs/ARCHITECTURE.md` | `ChartGen_Architecture.md` Sections 2-4, decisions removed |
| `docs/DATA_FORMATS.md` | `ChartGen_Architecture.md` Section 5 - `.cgw` layout, all column schemas |
| `docs/GLOSSARY.md` | `ChartGen_Glossary.md`, Base Table count corrected to 4 |
| `docs/FEATURES.md` | `ChartGen_Feature_List.md` |

Do not carry forward: `ChartGen_Primer.md`, `ChartGen_Docs_Maintenance_Guide.md`.

**Decision cull.** The 50 Architecture decisions are culled, not archived. For each first pass produce two lists for approval: proposed cull, and facts extracted from culled entries needing a new home. Extract before deleting.

Known extraction targets: Decision 48 (scaling mechanism, four call sites), Decision 50 (four Base Tables).

Correct on migration:
- `shapes/common.py` and `base_charts/registry.py` state three and four canonical shapes. There are five.
- `CHART_REGISTRY` holds 33 Base Charts.

**At end of stage:** delete `dynamic_docs/` entirely - `Current_State.md`, `Next_Session.md`, `Progression_Log.md`, `Decisions.md`. No archive.

---

## Stage 3 - CLAUDE.md files

Root first, then packages.

### Root `CLAUDE.md`

*Lead: Chat - design discussion, short output, gates Stage 4*

120-180 lines, hard ceiling 200. Contains: what ChartGen is (3 lines), how to run it, orientation map (one line per package), standing rules, pointers to `docs/`.

Standing rules proposed for review, not agreed:
- No defensive coding. No silent clamps, drops on mismatch, or fallback defaults. Fail visibly.
- Stored values are never rewritten.
- Validate only where designed. Raise before adding validation.
- Base Charts and Base Tables are outside the system boundary. Do not refactor, deduplicate, or extract shared helpers.
- Design before build.

Approval of these rules gates Stage 4.

### Package `CLAUDE.md` files

*Lead: Claude Code*

| Location | Covers |
|---|---|
| `chartgen/acquisition/` | Two toolkits, URL triage, transformer output contract |
| `chartgen/shared/normalisation_containers/` | Five canonical shapes, `Unit`/`ShapeStats`, dispatch |
| `chartgen/output_generation/execution/` | Assembly pipeline, `CHART_RENDER_SCALE` and call sites |
| `chartgen/output_generation/definition/running_order/` | Running Order contract, column schema |
| `chartgen/ui/` | Streamlit patterns, logic delegated to owning modules |
| `chartgen/workfile/` | `.cgw` lifecycle, state ownership |
| `.../charts/base_charts/` | Contract, scaling mechanism in full, do-not-refactor fence |
| `.../tables/base_tables/` | As above, full duplicate |

Harvest from `shapes/__init__.py`, `base_charts/registry.py`, `base_tables/registry.py`.

### Scaling explanation

Written in full in both `base_charts/CLAUDE.md` and `base_tables/CLAUDE.md`. Duplicated, not cross-referenced.

Each copy must cover:
- PowerPoint's SVG compression pass and how it mis-spaces `<text>` characters
- The draw-big-then-shrink mechanism
- Why a post-render transform wrapper does not fix it
- `TEXT_SCALE` multiplies absolute point-based literals only, never fractional, figure-fraction, or data-space values
- Current value: 5
- Must match call sites: `assembly_engine.py`, `insert_table.py`, `charts_tab.py`, `output_tables_tab.py`
- Not enforced in code; a mismatch fails silently in one file only

Sufficient for a human or Claude to understand the mechanism from cold.

---

## Stage 4 - Docstrings, system layer

*Lead: Claude Code*

Roughly 60 files. One package per pass, reviewable diff each pass.

Includes `base_charts/registry.py` and `base_tables/registry.py`.

**Convention.**
- Module docstring: 1-3 lines, what it does.
- Function docstring: only where the signature does not already say it. Contract only - parameters, return, raises, non-obvious preconditions.
- Inline comments: only where the code alone misleads.

**Remove:** session history, decision references, rationale, "mirrors X" comparisons, rejected alternatives.

**Test for keeping a line:** does it change what gets done. If not, remove it. Text written to justify a decision, or to reassure a reader it was sound, reads as fact on the next pass and is the origin of most of what is being stripped here.

**Flagged cases.** Strip aggressively by default. Queue anything that may carry value; review in batches per package. Kept content goes to the package `CLAUDE.md`, a short inline comment, or `ARCHITECTURE.md`.

Known flag: `base_charts/registry.py` warns that externally-authored Base Chart files arrive with stale or colliding internal names, and a name match is not evidence of intended replacement. Appears in no governed document.

---

## Stage 5 - Docstrings, Base Charts and Base Tables

*Lead: Claude Code*

Full strip across all 37 files.

Remove the per-file `TEXT_SCALE` comment entirely. No residual pointer line.

---

## Open items

1. Adopt `.claude/rules/` path-scoped rules - deferred.
2. Replacement for the Wake up, Close-down and Scrap Session protocols.
3. Confirm lead surface for Stages 2 and 3 after Stage 1 completes - provisional.
