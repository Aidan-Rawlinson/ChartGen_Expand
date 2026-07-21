<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the five governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.

## Status: Previous session's "quick wins + UI polish" work stands unchanged. This session was prototype-sharing prep, not functionality work: planned what's needed to hand a working prototype to a colleague, wrote real per-tab guidance content, built it into a 9-page PDF, and wired the real guidance links into code. No ChartGen behaviour changed.

### What works (built this session)

- **Guidance links now point at real content.** `core/ui/common/guidance.py`'s `GUIDANCE_URLS` swapped from placeholder `bbc.co.uk` links to a real SharePoint-hosted PDF (`ChartGen_Tab_Guidance.pdf`), one `#page=N` anchor per tab (Imports p3, Populations p4, Select p5, Text p6, Running Order p7, Charts p8, Outputs p9). Confirmed by the user that the direct SharePoint file URL (not a "Copy link" share-token URL, and not `?web=1`) honours the `#page=N` fragment in their environment. Stale `"details"`/`"config"` dict keys (left over from last session's tab removal) deleted at the same time — no other code in the file needed to change.
- **`ChartGen_Tab_Guidance.pdf` — a 9-page reference guide, one page per tab plus a cover/contents page.** Built with ReportLab against a client-supplied style guide (NHSBN palette/typography, A4, cover block + contents list, banded tables). Content was written from the actual tab source files (`core/ui/tabs/*.py`, `core/ui/workfile/*.py`) and the Functional Spec/Glossary, not just the short descriptions used in earlier drafts — covers every button and control per tab, including ones not previously referenced anywhere (e.g. the Open Workfile lock-decision states, the Charts tab's Period Range/Convert-to-Metrics/Sizing/Zoom controls, Outputs' preflight checks). The Text tab's entry in particular was expanded from a one-line stub into a full explanation of the text-tag mechanism itself (paragraph-level `update_text` replacement, table cells not yet covered), not just a description of the tab's current single-tag preview.
- **This PDF and its build script exist only in SharePoint / this session's sandbox — by explicit user choice, they were not saved into the project folder.** If the guide needs updating later, it will need rebuilding from scratch (a fresh content pass against the tab code), not just an edit to a saved script.

### Prototype-sharing plan (in progress, not yet complete)

Colleague will use their own toolkit login; no pre-built sample workfile — user is building sample PowerPoint templates themselves (two or three, varying complexity). Outstanding items:
- **Quick-start guide** — a walkthrough of using the tool end-to-end against the sample PowerPoints. Not started.
- **Sample PowerPoint templates** — user's own task, in progress on their side.
- **Installer check** — confirm the colleague can get ChartGen running on their own machine with their own login. Not started.
- Known-issues briefing was explicitly ruled out by the user — this is a look/feel/usability prototype, not an alpha or beta, so untested-detail caveats aren't being surfaced to the colleague.

### Known gaps / not yet done

- **Sidebar divider line — abandoned as not worth the effort, by explicit user call.** Wanted a thin grey line between button groups; tried many techniques (`st.divider()`, raw `<hr>` with margin/padding/fixed-height-flex-box, dash-character text, absolute positioning) — every attempt showed the same "space above works, space below collapses to zero" pattern, or (with dashes) the box's visible size not matching its allocated layout space. Root cause never identified. Final state: plain empty spacer `div`s (32px) between groups, no line, no text — user confirmed this looks good. Any future attempt at a divider line should expect the same fight.
- **Sidebar/main-content CSS spacing — partial, accepted, not chased further.** `core/ui/common/layout_css.py` targets: main content top padding (`block-container`/`stAppViewBlockContainer`/`stMainViewBlockContainer`, unclear which applies to this install), the sidebar's `stSidebarHeader`/`stLogoSpacer` (the collapse-arrow bar + an unused logo spacer — confirmed via browser inspection to be the real source of the sidebar top gap, not `block-container`), `stSidebarUserContent` padding, and the sidebar's inter-element `gap`. User confirmed some visible improvement (button gaps, some top-gap reduction) and explicitly said they're okay with the remaining gap — not pursued to perfection.
- **Process-restart gotcha, worth remembering for any future CSS/UI iteration:** the user's `.bat` launches a real background server process in a command prompt window; closing the Edge tab does *not* stop it. Several "no change" reports this session were actually stale-server false negatives — resolved once every leftover `python.exe`/command-prompt window was killed via Task Manager before rerunning. Flag this early if UI changes ever appear not to be taking effect.
- **Sidebar dirty marker (●) for unsaved changes was dropped and never restored.** It used to sit next to the workfile name in a title line that's since been removed (per user instruction — the file name wasn't useful; the red description badge at the top of the main content area is the real "what am I working on" signal). Nowhere in the sidebar currently shows "you have unsaved changes" at a glance. Not raised again after being flagged — treat as accepted unless the user brings it up.
- Table-wide chart_type_ref/metric_periods validation on Excel upload — still explicitly deferred by the user from an earlier session, not yet scoped.
- Population-table Excel edits still have no validation (dangling `soft_parents` possible) — same deferral.
- No live batch-run test yet for Period Range / Convert Periods to Metrics, or for the format_modifier/placeholder-removal work — both built in an earlier session, still untested against a live run.
- TimeSeries charts and the Charts sheet round-trip more broadly still haven't had a real batch-run test pass into a live template.
- Tweaks (reference lines, axis control, conditional colouring, hook architecture) — not built.
- One-hop-only `soft_parents` resolution — deliberate scope boundary, not a bug.

### Resolved / dropped this session

- Guidance link placeholders — resolved. Real SharePoint-hosted PDF wired in, dead `"details"`/`"config"` dict keys removed (see above).

### Noted, not yet actioned

- Prototype-sharing plan is mid-flight — see "Prototype-sharing plan" above for the three outstanding items (quick-start guide, sample templates, installer check).
