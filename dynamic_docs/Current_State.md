<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE -- READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the six governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base -- which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously -- during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in -- expect churn, don't resist it.
>
> **Standing rule (confirmed by the user, still in force): Base Charts and Base Tables are never documented in the governed docs -- not their existence, not their internals.** Only a genuine core-system-level change belongs there. Do not log a new Base Chart/Table's existence "for completeness."

## Status: Every Excel export/import round-trip across the app (chart URL manifest, Running Order, Chart Store, Stat Tags, Output Table grids, population tables) moved from browser download/upload widgets to a fixed `CG_Extracts` folder alongside the `.cgw`. Governed docs updated and re-uploaded as of this close-down.

### This session's work

**Excel round-trips moved from `st.download_button`/`st.file_uploader` to `CG_Extracts`, Architecture Decision 42.** Started as a scoped request (Output Tables only) then widened, on request, to every Excel round-trip in the app once the underlying architectural constraint was surfaced: Streamlit's browser widgets give server-side code no way to choose a download's destination or default an upload dialog's folder. New shared helper `core/shared/infrastructure/cg_extracts.py` (`get_extracts_folder`) resolves/creates a `CG_Extracts` folder next to the `.cgw`. New picker `core/ui/common/pickers.pick_xlsx_file` extends the existing native-`tkinter`-dialog pattern (previously `.cgw`-only) to `.xlsx`, defaulted to `CG_Extracts` via `initialdir` but not restricted to it.

Every `write_*_xlsx`/`read_*_xlsx` function already took a plain path, so no reader/writer code changed — only the UI layer. Pattern is identical across all six locations: a plain `st.button` for export (writes straight to disk, no dialog, `st.success` confirms the path) and a plain `st.button` for import (opens the native picker, reads straight from the picked path). Converted: `imports_tab.py` (chart URL manifest), `charts_tab.py` (Chart Store), `output_tables_tab.py` (grid), `populations_tab.py` (each population table), `running_order_tab.py` (Running Order — missed on the first pass, caught and fixed after user testing), `text_tab.py` (Stat Tags). Filenames unchanged throughout. Confirmed explicitly out of scope: the Custom Charts/Custom Tables `.md` bundle downloads (code hand-off to an AI) — not an Excel round-trip, left on `st.download_button`.

**Governed docs updated for the above** — Architecture (new Decision 42), Feature List, Functional Spec (six wording updates across the Imports, Populations, Running Order, Output Tables, Chart Store, and Stat Tags sections). Glossary and Primer untouched — nothing this session changed domain rationale or introduced a new term needing definition.

### Known gaps / not yet done (carried forward, none touched this session)

- **The same `cell.value`-without-`number_format` gap may exist in Stat Tags', Chart Store's, and the Running Order's own Excel readers** -- only the Output Table content path has been fixed; the others are an un-investigated, live risk of the same failure mode.
- **Base Table trim (from an earlier session) is still a potential breaking change** for any existing workfile using one of the eight removed styles -- not confirmed clear with the user.
- **SVG transparent backgrounds for tables** -- still deferred, case-by-case, per the user's own earlier plan.
- **A residual "pixel or two too low" vertical offset in `table_cardtile`'s chart-cell placement** -- still parked, not investigated.
- **Any Running Order `.xlsx` already generated under the old (pre-fix) two-`tweaks`-column schema still needs regenerating** -- carried forward from an earlier session, not touched this session.
