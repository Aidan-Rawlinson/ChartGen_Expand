<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

- **No specific next feature named at close of this session.** Ask rather than assume a direction.
- **Full sweep for browser-widget Excel round-trips was done this session — confirmed clean.** `grep`-style search across `code_base` for `download_button`/`file_uploader` turns up only the Custom Charts/Custom Tables `.md` bundle downloads (confirmed out of scope, unchanged) and the PowerPoint template uploader on the Imports tab (a different, unrelated flow). No further Excel round-trips need converting.
- **Native `tkinter` file dialogs (both `.cgw` pickers and the new `.xlsx` picker) haven't been stress-tested for edge cases** — e.g. behaviour if `CG_Extracts` is deleted mid-session between export and import, or if the workfile's own folder is on a network drive with slow directory listing. Nothing reported broken; just not deliberately tested beyond normal use.
- **The same Excel `cell.value`-without-`number_format` gap fixed for Output Table content (Architecture Decision 34) may still exist in the Stat Tags, Chart Store, and Running Order Excel readers.** Flagged repeatedly now, still not investigated.
- **Base Table trim (from an earlier session) is still an unconfirmed, potential breaking change** for any existing workfile using one of the eight removed styles -- carried forward across several close-downs now.
- **SVG transparent backgrounds for Output Tables** -- still deferred, case-by-case, per the user's own earlier plan.
- **A residual "pixel or two too low" vertical offset in `table_cardtile`'s chart-cell placement** -- still parked, not investigated.
- **A larger, unscoped feature raised in conversation some sessions back: conditional per-unit slide deletion plus a matching index-page regeneration.** Still needs its own dedicated design session. Nothing built yet.
- **Any Running Order `.xlsx` already generated under the old (pre-fix) two-`tweaks`-column schema still needs regenerating** -- carried forward from an earlier session.
- **`CG_Chart_`/`CG_Link_` shape naming only applies to charts inserted from this point forward** -- carried forward, still relevant if the Position Finder tool is reported "not finding" a match on an older output.
- **The `target` tweak convention is intentionally per-chart, not a system standard** -- carried forward; don't assume a third chart's tweak needs the same syntax without asking.
- **The relative-to-chart-corner picture positioning built for the hyperlink icon is a reusable pattern, not yet extracted anywhere** -- carried forward, still only living in `assembly_engine._insert_hyperlink_icon`.
- **An unbuilt idea from an earlier session: letting a template textbox sit in front of an inserted chart picture rather than behind** -- confirmed buildable, not built, carried forward.

## This session's work, for context

Started as a scoped request — Output Tables' Excel export/import should write to/read from a `CG_Extracts` folder next to the `.cgw` instead of the browser's Downloads folder. The design conversation surfaced a real architectural constraint (Streamlit's `download_button`/`file_uploader` are browser-sandboxed; server code can't dictate a download's destination or an upload dialog's default folder), which reframed the fix as "replace the widgets with direct filesystem write + native OS picker," not "add a path parameter." Scope was then widened, on request, to every Excel round-trip in the app.

Built: `core/shared/infrastructure/cg_extracts.py` (new), `pick_xlsx_file` added to `core/ui/common/pickers.py`, and six tabs converted (`imports_tab.py`, `charts_tab.py`, `output_tables_tab.py`, `populations_tab.py`, `running_order_tab.py`, `text_tab.py`) to the same Export/Import-button pattern. The user caught that Running Order was missed on the first pass (four tabs were converted, then confirmed working, before the gap was raised) — a full codebase search on the second pass caught Running Order and Stat Tags together, plus a leftover dead `ro_buffer = io.BytesIO()` line from an editing slip, fixed before close-down.

Governed docs (Architecture — new Decision 42, Feature List, Functional Spec) were updated at the user's request, immediately before this close-down. Glossary and Primer were left untouched — no new term, no change to domain rationale.
