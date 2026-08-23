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

## Stage order changed

Stages 2 and 3 swapped. Stage 3 runs first.

Reason: the plan produced the reference documents before the operative ones, so Stage 2 had to guess what Stage 3 would want. `ARCHITECTURE.md` absorbed rules that belong next to the code and would have had to move out again.

Revised order: Stage 3 (`CLAUDE.md` files), then `DATA_FORMATS.md`, `GLOSSARY.md`, `FEATURES.md`, then `ARCHITECTURE.md` last, written from what no other document claimed.

`CLAUDE.md` scope widened: one in every package with something operative to say, not the eight originally listed. Content sits closest to the code it governs. Root is kept thin because the content lives below it.

Cull standard raised: delete anything that is justification or explanation. Keep a fact only if it is helpful and not obvious in the code.

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

Do not carry forward: `ChartGen_Primer.md`, `ChartGen_Docs_Maintenance_Guide.md`, `ChartGen_Functional_Spec.md`.

The Functional Spec is dropped, not redistributed. It recorded why the system works as it does. Its abstraction level does not survive being read back by an LLM across a growing codebase, and Aidan holds that understanding directly. Decided at the start of Stage 2.

**Decision cull.** The 50 Architecture decisions are culled, not archived. For each first pass produce two lists for approval: proposed cull, and facts extracted from culled entries needing a new home. Extract before deleting.

Known extraction targets: Decision 48 (scaling mechanism, four call sites), Decision 50 (four Base Tables).

Correct on migration:
- `shapes/common.py` and `base_charts/registry.py` state three and four canonical shapes. There are five.
- `CHART_REGISTRY` holds 33 Base Charts.

**At end of stage:** delete `dynamic_docs/` entirely - `Current_State.md`, `Next_Session.md`, `Progression_Log.md`, `Decisions.md`. No archive.

Stage 2 outcome:
- `DATA_FORMATS.md` 438 lines, `FEATURES.md` 234, `GLOSSARY.md` 204, `ARCHITECTURE.md` 164. 1040 total, replacing roughly 282KB of source.
- Every schema, field list, constant and count in `DATA_FORMATS.md` was checked against the code. The source was accurate on all of them except the ones already known stale.
- `workfile_info.json` carries a seventh key the source document omits: `file_version_id`.
- A `TABLE_SANDBOX_FIELDS` exists alongside `CHART_SANDBOX_FIELDS` and appears in no source document.
- `settings.csv` is an open key-value store, not a fixed schema. Documented as such, with the 17 keys currently in use.
- `Metric-Series` is used throughout the codebase and was defined nowhere. Now in `GLOSSARY.md`.
- Culled from the glossary: the Package Map, which duplicated the architecture layout, and most of the general Python terminology.
- `ARCHITECTURE.md` cut from 337 lines to 164 once the operative content moved to `CLAUDE.md` files. It now carries the principles, the two domains, the layout, a report-assembly walkthrough, and a signpost table.
- `dynamic_docs/` and `static_docs_mirror/` both deleted, 12 files, on Aidan's instruction. `static_docs_mirror/` was outside this plan's original scope; deleting it was authorised at the end of Stage 2. All 12 were git-tracked, none untracked, so all are recoverable from history.
- Removed with `static_docs_mirror/`: `ChartGen_Architecture.md`, `ChartGen_Glossary.md`, `ChartGen_Feature_List.md`, `ChartGen_Functional_Spec.md`, `ChartGen_Primer.md`, `ChartGen_Docs_Maintenance_Guide.md`, `Project_Instructions.md`, `README.txt`.
- The staged deletions are not yet committed.

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

Stage 3 outcome:
- 21 files, 526 lines total. Root 45 lines. The two scaling files are 67 and 76; every other file is 3 to 33.
- Written: root, `acquisition/` and its `toolkit_nhs/`, `toolkit_indicators/`, `template/`; `definition/running_order/`; `execution/` and its `charts/base_charts/`, `charts/custom_charts/`, `tables/`, `tables/base_tables/`, `tables/custom_tables/`, `text/`, `pptx_com/`, `excel/`; `shared/` and its `infrastructure/`, `normalisation_containers/`, `normalisation_containers/shapes/`; `ui/`; `workfile/`.
- Skipped as having nothing operative to say: `manifest_table/`, `pictures/`, `static_config/`, `session_shell/` and its subpackages, `ui/tabs/`, `ui/common/`, `ui/workfile/`, `workfile/setup/`, `workfile/state/`, the four `base_charts/` shape subfolders, and the pass-through `output_generation/`, `definition/`, `charts/` levels. An empty file costs a read and returns nothing.
- The scaling explanation's required point "why a post-render transform wrapper does not fix it" traces to nothing in the code or the source documents. Dropped, not written. Requirements in this plan that cannot be traced to the codebase or a recorded observation are not facts and are not carried into a document.
- Standing rules are written into the root file as authoritative. They were meant to be approved first. They still need a yes before Stage 4.
- `docs/ARCHITECTURE.md` was written under the old order and now duplicates these files. It is cut back at the end of Stage 2, not now.

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

Changed on Aidan's instruction: one consolidated borderline list at the end of the full sweep, not batches per package.

Stage 4 outcome:
- Scope was 111 non-empty files, not the "roughly 60" this plan assumed. 77 changed.
- Prose down from 5,047 lines to 4,371, a 13% cut. Docstrings 3,645 to 3,198; comments 1,402 to 1,173.
- Dead references to deleted documents: around 100, now zero.
- 13% rather than 40% because the remaining prose is contract statements and framework constraints. All history, dead references and self-justification are gone. Cutting further would mean deleting return-value contracts and Streamlit ordering notes, which a reader needs.
- One out-of-scope edit, kept deliberately: a `Decisions.md` reference removed from `custom_tables/bundle.py`'s AI-facing string constant. Both `*_INPUTS_EXPLANATION` constants left byte-identical, verified by hash.
- A regex removing dead-reference parentheticals mangled two comments where the parenthetical spanned a line prefix. Both caught by the verification harness, rewritten by hand, whole codebase re-checked.
- Verification: every file compiles, all 181 modules import cleanly, AST comparison against HEAD confirms no code changed, and the app starts and renders the sign-in gate with no errors.

Stage 4 close-out, after review of the borderline list:
- All 14 items decided. Final prose figure 5,047 lines to 4,360, a 14% cut.
- New standing rule, generalised from one objection to a count of "the four data shapes that have charts": **name the set, never count it.** A derived count rots the moment a file is added, and a count that partitions things into done and not-done reads as a design boundary rather than a snapshot of incompleteness. Every count of that kind stripped from the four documents and the `CLAUDE.md` files.
- The rule does not extend to a closed, designed set. "Three scopes", "three yellow-box outcomes", "two domains" all stay: adding a member there would be an architectural act, so the count carries meaning and should be wrong when the design changes.
- `autoCompressPictures="0"` confirmed settled; the UNRESOLVED note removed.
- The `filter_time_series_periods` claim that "the agreed design is padding with placeholder periods" traces to nothing and was removed. The behaviour it described is real and moves to Stage 7.
- `ORGANISATION_ID = 232` is a placeholder organisation, not a real one, and correctly hardcoded. Comment corrected to say so.
- `has_valid_unit_data` left in place; revisit when the tool is mature if still unused.

Known flag: `base_charts/registry.py` warns that externally-authored Base Chart files arrive with stale or colliding internal names, and a name match is not evidence of intended replacement. Appears in no governed document.

---

## Stage 5 - Docstrings, Base Charts and Base Tables

*Lead: Claude Code*

Full strip across all 37 files.

Remove the per-file `TEXT_SCALE` comment entirely. No residual pointer line.

Settled at the end of Stage 4: the four system-layer `CHART_RENDER_SCALE` markers stay. This stage still removes the per-file `TEXT_SCALE` comments with no pointer.

**Floor agreed at the start of the stage.** Two things may survive per file, nothing else:
1. One line of module docstring - what kind of artefact it is, its shape, what it draws.
2. One line where the file reads `tweaks` with its own grammar. This is the only content in these files not recoverable from a `CLAUDE.md` or the bundle contract, and it is user-facing.

**Why stripping does not weaken the standalone export.** `bundle.py` embeds `custom_charts/contract.py`'s `CHART_INPUTS_EXPLANATION` above the file's own source in every bundle. That constant already covers the `.crtx` framing, the full `chart_inputs` contract, `population_layers` semantics, EMU, the 5x pre-scaling and the PowerPoint reason for it, `TEXT_SCALE = 5` with the scale/never-scale rule, Calibri and `svg.fonttype`, allowed imports, and the return contract. The per-file prose repeated all of it. Stripping removed duplication from the bundle, not information.

Stage 5 outcome:
- Scope was 45 files, not the 37 this plan assumed: 33 Base Charts, 4 Base Tables, 7 `__init__.py` files, and the 2 `registry.py` files already done in Stage 4 and left alone. 44 changed.
- Prose 2,075 lines to 89. Docstrings 1,340 to 89, comments 735 to 0. Tree 7,141 lines to 5,254. 149 insertions, 2,034 deletions.
- Of the 89 surviving lines, 44 are the two untouched `registry.py` files. The 43 stripped files carry 45 lines between them: one each, plus a second in `column_ci_full` and `line_ci_full` for their `tweaks` grammar.
- The 7 `__init__.py` files were added to scope this session. Stage 4 had skipped them. `base_tables/__init__.py` still cited the deleted `Decisions.md` and said two Base Tables exist when there are four. Both corrected. Dead references across both trees: 16 lines before, zero now.
- `tweaks` grammar kept, in two files only: `column_ci_full` (`target:N`, `target:median`) and `line_ci_full` (the same, plus the bare `12m` flag). Both are typed by the user into a Running Order cell.
- Edits were made by an AST-driven tool working off docstring and comment line numbers, not by regex, per the Stage 4 finding that a regex sweep mangled two comments.

Verification:
- Every file compiles; all 181 modules in `chartgen/` import cleanly.
- AST comparison against HEAD with docstring nodes stripped from both sides: no code changed in any file.
- **All 33 Base Charts and all 4 Base Tables rendered from synthetic data and compared byte-for-byte against the same renders from a HEAD worktree. Identical.** This needed matplotlib's own nondeterminism normalised out first: it stamps a wall-clock `<dc:date>` and a random id per clipPath, marker and glyph path. Ids are canonicalised by ordinal of first appearance. Two runs of the same tree agree before the comparison is trusted.
- Both bundle documents build from the stripped sources, with the contract section intact and the source section carrying the complete file.
- `CHART_INPUTS_EXPLANATION` and `TABLE_INPUTS_EXPLANATION` byte-identical to HEAD, verified by parsing the constant out of both.
- App starts headless and serves the sign-in page, HTTP 200, no errors logged.

Borderline items stripped, listed for a decision rather than silently kept:
- `bead_string_dot_plot`, the visual-only de-duplication comment: a unit shown in a more specific tier is suppressed from broader tiers, and the stats are computed before this so they are unaffected.
- The `line_ci_*` family's epsilon note: the `+/- 0.0001` is not a float tolerance, it is there so a value exactly equal to the threshold passes.
- `_find_selected_in_scope` and `_selected_identity` return-tuple contracts, `(index, value, unit_code)` or `(None, None, None)`.
- `plain_grid`'s entry-point parameter shapes: `content` is N rows by M columns, `column_widths` length M, `row_heights` length N, both percentages.
- `sparkline1`'s note that a Base Chart must return the requested size itself rather than relying on the inserter to stretch a cropped file back.

Raised, not fixed:
- The 44 rewritten files are LF in the working tree while `core.autocrlf` is `true`, so Git normalises them on commit and restores CRLF on the next checkout. The working tree was already mixed before this stage. No effect on committed content.

### Stage 5 follow-up - the TEXT_SCALE claims, resolved

Two `TEXT_SCALE` claims raised at the Stage 5 close-out are now corrected. Settling them turned up a design fact that was recorded nowhere.

The old claim in `base_charts/CLAUDE.md` was that a file computing its sizes proportionally needs no `TEXT_SCALE`, and that the `line_ci_*` family works this way. The mechanism was right, the attribution wrong: `line_ci_full` is in that family and defines `TEXT_SCALE = 5`.

**Why `line_ci_na` needs none.** Not because its "N/A" is large enough to tolerate the mis-spacing. Its font size is 8.73pt at real size and 43.63pt as the chart is actually called, so it is already drawn at 5x and gets the same protection as every other file. The route differs, not the outcome: the font size derives from the circle radius, the radius from the canvas, and the canvas arrives pre-multiplied.

**The constraint.** Any expression that tracks the cell already carries the 5x, so `TEXT_SCALE` cannot also appear in it without double-applying. Cell-tracking text and visible-`TEXT_SCALE` text are mutually exclusive, not stylistic alternatives. This matters because `insert_table.py` calls a chart at its cell's own rectangle: hardcoding `line_ci_na`'s font size would leave it correct only at the default 2.99 by 0.75in, a speck in a 6-inch cell and an overflow in a 1.2-inch one. Measured font sizes across those three cells today: 23.3pt, 43.6pt, 116.6pt.

So the rule is not "no text, no `TEXT_SCALE`", and no file is getting a pass. Every text-drawing chart draws at 5x by one of two routes. The nine single-indicator charts draw no text at all.

Changed:
- `charts/base_charts/CLAUDE.md`: the wrong paragraph replaced with the two routes and the constraint that keeps them apart.
- `execution/CLAUDE.md`: "must match `TEXT_SCALE` in every Base Chart and Base Table file" corrected to "in every file that defines one". 10 of the 37 have none.
- `timeseries/line_ci_na.py`: a two-line comment on the font-size line, saying it is already inflated and a `TEXT_SCALE` would double-apply. **A deliberate exception to the Stage 5 decision that these files carry no residual `TEXT_SCALE` pointer line.** It earns the exception because the absence of the constant is what invites someone to add one and break the render.

Withdrawn: the `base_tables/CLAUDE.md` "every file here" flag. All four Base Tables define `TEXT_SCALE` and a Base Table without text is not a real prospect, so the row is correct and a hedge would be noise. The flag was a weak call.

Verified: `line_ci_na` renders byte-for-byte identically to `42ef3b9` at all three cell sizes, and the font size still tracks the cell.

---

## Stage 6 - Dead code removal

*Lead: Claude Code*

Permission for functional change is granted for this stage. Deletion only; no behaviour is intended to change.

Known instance: `render_table` in `tables/base_tables/registry.py`, re-exported from `__init__.py` and listed in `__all__`, with no callers anywhere.

**Method.** Build the set of module-level definitions across `chartgen/` from the AST, then the set of referenced names, and diff. Produce a candidate list for approval, then delete in one pass.

**Confirm every candidate by hand.** Three things look dead and are not:

- **String dispatch.** `FUNCTION_MAP`, `CHART_REGISTRY` and `TABLE_REGISTRY` reach their targets by string key, so every Running Order function and every Base Chart and Base Table appears unreferenced. Roughly 50 functions.
- **Re-export shims.** `dialog_support.py` re-exports the `period_ids` helpers; `ui/common/formatting.py` re-exports `format_number`. Both marked `noqa: F401`, both load-bearing for their old call sites.
- **Streamlit entry points.** Tab render functions are called from `app.py` only, and some helpers only from inside a widget callback.

Stage 6 outcome:
- 15 deletions across 18 files. 118 lines removed, 22 added. No behaviour change.
- All three warned categories were real and all produced false positives. Every one was cleared by hand.

Deleted, functions with zero callers:

| Where | Name |
|---|---|
| `charts/base_charts/registry.py` | `render_chart` |
| `tables/base_tables/registry.py` | `render_table` |
| `execution/tables/grid_store.py` | `get_table_id`, `set_content_cell` |
| `shared/infrastructure/soft_parents.py` | `related_tables` |
| `workfile/setup/new_workfile.py` | `list_projects_for_year` |
| `acquisition/toolkit_nhs/api_client.py` | `get_projects` |

`render_chart` and `render_table` were superseded by `get_chart_callable` and `get_table_callable`, which check saved Custom Charts and Tables as well as the built-in registry. `render_table`'s own docstring already said "UNUSED". Each took three edits: the `def`, the `__init__.py` import, the `__all__` entry.

Deleted, constants with no consumers: `TIMESERIES_TABLE_PREFIX` (`toolkit_indicators/population_tables.py`), and `CONTENT_FUNCTIONS` and `BATCH_FUNCTIONS` from `running_order/schema.py` with their `__init__.py` import and `__all__` entries. `STRUCTURAL_FUNCTIONS` stays: used once, at `xlsx_writer.py:190`. The three read as a designed taxonomy but only one third of it was ever consumed and the split appeared in no document.

Deleted, unused imports: `MANIFEST_FIELDNAMES` (`manifest_table/xlsx_reader.py`), `CustomChartError` (`custom_charts/resolve.py`), `CustomTableError` (`custom_tables/resolve.py`), `io` (`pictures/insert_picture.py`), `merge_custom_refs_for_shape` (`ui/tabs/charts_tab.py`). Neither exception import was load-bearing; each package's `__init__.py` takes the exception from `gate` directly.

**One cascade.** Deleting `list_projects_for_year` orphaned `get_projects`, its only caller, which was then deleted on Aidan's decision. It was the only function in `toolkit_nhs/api_client.py` with no callers; the other six are all used. Its `/projects/list` endpoint and its `isVisible.description == "Yes"` filter are recoverable from Git history if project listing is ever wanted again. Removing it and its import also made `workfile/setup/new_workfile.py`'s own docstring true for the first time: it claims "no NHS toolkit involvement of any kind" while importing from the NHS api_client.

**The analyser needed three fixes before its output could be trusted.** Each had been inventing candidates:
- Relative imports (`from .transformers import transform`) were unresolvable, so all 10 acquisition-layer functions showed as dead.
- An aliased import rebinds the name, so `new_workfile` showed as dead while `workfile/setup/new_workfile.py` imports it as `_create_workfile_file`.
- `import x.y` then `x.y.func()` is attribute access, not a name load, so all 8 Streamlit tab functions showed as dead.

A fourth limitation was left in place because it only over-reports: the analyser cannot follow a re-export chain more than three hops, which is why `build_metric_periods_string` still shows as unreferenced. It reaches `charts_tab:835` and `text_tab:236` through `period_ids` to `dialog_support` to `running_order/__init__`.

Prose corrected, since deleting `render_chart` orphaned five references and leaving them would reintroduce what Stage 4 removed: `assembly_engine.py`, `charts_tab.py`, `custom_charts/resolve.py`, `base_charts/registry.py`, and the assembly walkthrough in `docs/ARCHITECTURE.md`. Also corrected while there: `report_context.py` claimed the context is "passed to render_chart", which was already false. It is held on the `AssemblyContext` and read by `update_text`, `insert_picture`, `insert_from_excel` and `insert_table`, never by a chart.

Not touched: the 33 Base Charts and 4 Base Tables. Only their two `registry.py` and two `__init__.py` files are in scope, being system-boundary plumbing.

Raised, not fixed:
- `_apply_spine_style` in `categorical_compositional/yn_bar.py` is defined and never called. `diverging_bar.py` carries the same helper and does use it. Left in place: these files are handed whole to an external AI and pasted back, so an edit there is lost the next time that happens, and the do-not-refactor fence covers them.

Verification: all 182 files compile and all 181 modules import; the analyser now reports only the 8 tab entry points, the `build_metric_periods_string` shim and `_apply_spine_style`; `CHART_REGISTRY` still holds 33 callables and `TABLE_REGISTRY` 4; all 33 charts and 4 tables render byte-for-byte identically to `ebfd25b`; both bundle documents build; the app serves its sign-in page, HTTP 200, no errors logged.

---

## Stage 7 - Fix the known defects

*Lead: Claude Code*

Permission for functional change is granted for these three items and no others. Raised during Stage 4.

**7.1 Id counter resync, all three id spaces.** `chart_store.next_chart_store_id` resyncs its counter to the true maximum among ids already in use before incrementing. `next_stat_tag` (`execution/text/stat_tags.py`) and `next_table_id` (`execution/tables/grid_store.py`) call `next_id` directly and do not, so the collision Decision 32 fixed for the Chart Store is still open for both.

Stat Tags is the live risk: `stat_tags_xlsx.assign_missing_tags` issues ids alongside imported ones. Reuse the existing pattern - an optional `existing_ids` set, decoded with `id_generation.from_base36` - rather than inventing a second one, and pass the set from each call site.

**7.2 Silent fallbacks.** Same family as the 50% sizing fallback removed at the end of Stage 3.

| Where | Now |
|---|---|
| `output_tables_tab.py` restore path | `min(200.0, float(pct))` silently caps a stored percentage above 200 |
| `output_tables_tab.py` restore path | `except (TypeError, ValueError)` substitutes 50% for an unparseable stored value |
| `shapes/timeseries.py` `filter_time_series_periods` | If `start_period_id` does not resolve but `end_period_id` does, the shape is returned completely untrimmed, discarding the end bound too |

**Behaviour agreed for the third.** Honour the end bound and treat the unresolvable start as "from the first period". The row renders rather than failing.

This scenario genuinely occurs in practice, and it does need action when it does. That action happens when the outputs are reviewed, by a person looking at the report. So the correct behaviour is to render what the shape actually has, not to fail the row and not to silently widen the range past the end bound the user set. Consistent with "an unresolvable period is a no-data case, not an error".

**Verification is behavioural.** There are no tests. 7.1 needs an xlsx import carrying pre-filled ids. 7.2 needs a row with a stored size outside 1 to 200, and a row whose `start_period` is absent from its report.

Stage 7 outcome:
- All three fixed. 7.1 and 7.3 sit in pure functions, so both were exercised directly rather than clicked through, and both tests were first run against the unfixed code to prove they bite.

**7.1.** `next_stat_tag` and `next_table_id` gained an optional `existing_ids` argument, resyncing the counter to the true maximum before incrementing. Copied from `next_chart_store_id` field for field, including the `try/except ValueError: continue` so an unrecognisable id cannot break the resync. One difference: a table_id carries no prefix, so nothing is stripped before decoding. The set is passed from all four call sites, with the running set updated per issue so two blanks in one import cannot collide either.

The collision was reproduced before the fix: a stat_tags.xlsx re-uploaded with tags T1 to T5 against a counter stale at 2 reissued **T3 and T4, both already in use**. Template text pointing at the original T3 would have resolved to the new row's value. After the fix the same input issues T6 and T7. Table ids reissued `3` against `1`-`5` in use; now `6`.

For table ids the exposure is narrower than expected and worth recording: no new `table_id` ever enters from outside, because the grid import assigns the imported grid to an id already chosen in the UI and ignores whatever sits in the file's A1. The remaining risk is a hand-edited `.cgw` whose counter has fallen behind its table CSVs. The existing-id set is the union of `output_table_rows` and the `output_tables` keys, since reading only one of them would be the same class of bug.

**7.2.** All three silent rewrites removed. A stored size now reaches the Sizing box unchanged, however small or large.

`max_value=200.0` came off all four Sizing widgets, because `st.number_input` raises if session state holds a value above its max, so a ceiling on the widget forces a clamp on the restore path and the clamp is the defect. Accepted side effect: a user can now type a size that runs off the page. The Resize Rows/Columns controls keep their own `max_value=200`, which is a real grid bound, not a sizing clamp.

An unparseable stored value is now reported with `st.error` and the session key left unset. **Not `st.stop()`**, which was considered and rejected: the restore runs once per session and the Reset control that clears a corrupted snapshot lives inside the tab, so halting the render would have removed the only route out. Reporting is enough - the substitution stops being silent, which was the defect.

**Scope addition, agreed:** `charts_tab.py` carried the same defect and worse - `min(200.0, max(1.0, float(pct)))` rewrote both ends, and the `max(1.0, ...)` floor turned a stored 0.5% into 1.0%, directly contradicting `ui/CLAUDE.md`'s own worked example of 0.03% displaying as 0.03%. Fixed alongside; leaving it would have had the two tabs silently disagree about the same stored value.

Checked while there and found clean: `percent_to_emu` and `emu_to_percent` carry no clamp of their own and round-trip losslessly at 0.03% and at 350%, so the whole stored-EMU-to-box-to-EMU path is now faithful.

**7.3.** The early return that discarded a resolved end bound when the start did not resolve is gone. An unresolvable bound now falls back to that end of the shape's own period axis, the same as a blank. The blank and unresolvable cases collapsed into one expression, so the `None` handling disappeared entirely and the function got shorter.

**Scope addition, agreed:** the unresolvable *end* was never settled by this plan and produced an empty range - the row rendered nothing. Fixing only the start would have left the function incoherent: an unresolvable start rendering from period 1 while an unresolvable end renders blank, for no reason a reader could infer. The same principle covers both. The empty-range branch remains, now reachable only when a resolvable start falls after a resolvable end.

A ten-case truth table over blank, resolvable and unresolvable at each end: four cases failed before the fix, all ten pass after.

**Comment corrections made in passing.** `charts_tab.py` claimed `filter_time_series_periods` "falls back to an empty range on an unmatched id", already wrong before this stage. And all four `CHART_RENDER_SCALE` comments repeated "must match `TEXT_SCALE` in every Base Chart and Base Table file", the same claim corrected in `execution/CLAUDE.md` after Stage 5; 10 of the 37 files define none. All five corrected.

`ui/CLAUDE.md` records the new rules: the Sizing box carries no upper bound and why, and the `st.stop()` decision.

Verification: 182 files compile and 181 modules import; both direct tests pass and were proved to fail on the unfixed code; all 33 charts and 4 tables render byte-for-byte identically to `1689810`, confirming 7.3 reached no further than intended; both bundle documents build; the app serves its sign-in page with no errors.

**Outstanding, needs a real workfile.** The 7.2 in-app check is the one thing not verified here: a Running Order row with a stored size outside 0 to 200 showing its real value, a row storing 0.5% showing 0.5% rather than 1.0%, and a hand-corrupted `output_tables_sheet_state` producing a visible error with Reset still reachable.

---

## Migration complete

All seven stages are done. Stage 5 `42ef3b9`, the `TEXT_SCALE` document corrections `ebfd25b`, Stage 6 `1689810`, Stage 7 as committed below.

## Open items

1. Adopt `.claude/rules/` path-scoped rules - deferred.
2. Replacement for the Wake up, Close-down and Scrap Session protocols.
3. The 7.2 in-app check, which needs a real workfile. See the Stage 7 outcome.

Item 3 of the original list, confirming the lead surface for Stages 2 and 3, is settled and dropped.

## Raised across the migration and still open

Recorded rather than fixed, each outside the stage that found it:

- **No `tests/` anywhere in the tree.** Stage 1. Every stage since has verified behaviourally, and Stage 7 had to hand-write throwaway harnesses for two pure functions that a test suite would have held permanently.
- **No version pins.** Stage 1. `requirements.txt` names 10 packages with no constraints, so every venv rebuild resolves to whatever is current on PyPI.
- **Tracked installer binaries.** Stage 1. `installer/Output/ChartGen.zip` and `ChartGen_Setup.exe` are in Git against the stated intent in `ChartGen.iss`. The `.gitignore` pattern matches now, but Git keeps tracking what it already tracks, so they stay versioned until explicitly untracked.
- **`has_valid_unit_data`** is unused. Stage 4. Revisit when the tool is mature if still unused.
- **`base_charts/registry.py`'s collision warning** - externally-authored Base Chart files arrive with stale or colliding internal names, and a name match is not evidence of intended replacement. Stage 4. Appears in no governed document.
- **`_apply_spine_style` in `categorical_compositional/yn_bar.py`** is defined and never called; `diverging_bar.py` carries the same helper and uses it. Stage 6. Left because these files are handed whole to an external AI and pasted back, so an edit there is lost the next time that happens.
