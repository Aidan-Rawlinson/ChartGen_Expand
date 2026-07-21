<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here — prototype-sharing plan (in progress)

The user needs a working prototype in front of a colleague shortly. Guidance content and links are done (see below); three items remain:

- **Quick-start guide.** A separate document from the tab guidance PDF — walks the colleague through actually using the tool (sign-in → New Workfile → Imports → ... → Outputs), built against the sample PowerPoint templates once they exist. Not started.
- **Sample PowerPoint templates.** User's own task — two or three, varying complexity. Check whether they're ready; the quick-start guide depends on them.
- **Installer check.** Confirm the colleague can actually get ChartGen running on their own machine, using their own toolkit login, from a fresh install — not yet verified.
- Explicitly **not** in scope: a known-issues/untested-detail briefing for the colleague. The user ruled this out — it's a look/feel/usability prototype, not an alpha or beta.

## This session's guidance work, for context

- `ChartGen_Tab_Guidance.pdf` (9 pages: cover/contents + one page per tab) is built and hosted on SharePoint at `.../TBNIntranet/Shared Documents/Resource Library/Tools & Templates/Internal Tools/ChartGen/Tab_Guide/ChartGen_Tab_Guidance.pdf`. `core/ui/common/guidance.py`'s `GUIDANCE_URLS` links all 7 tabs to it with the correct `#page=N` anchor, confirmed working by the user in their browser.
- **The PDF's build script was not saved anywhere** — the user explicitly declined saving it into the project folder. If the guidance content needs updating later, it means writing it again from scratch (re-reading the tab source files and rebuilding with ReportLab), not editing an existing script.
- The Sidebar has its own page in the PDF (page 2) but deliberately has no in-app guidance link — there's no `"sidebar"` key in `GUIDANCE_URLS`, and the user chose to leave it that way rather than add a new UI element for it.
- If more detail is ever wanted on other governed-doc facts not yet written up (e.g. sidebar button availability conditions, which came up while writing the guidance content but live only in code, not in the Functional Spec), that's a separate documentation-update conversation, not something done as part of this guidance PDF.

## Open decisions from an earlier session, don't relitigate

- **Sidebar divider line — dropped, by explicit user call after extensive attempts.** Every technique tried (native `st.divider()`, raw `<hr>` with various spacing approaches, dash-character text, absolute positioning) hit the same "space above works, space below collapses" pattern, or a box-size/layout-space mismatch. Root cause was never identified. Current state: plain empty spacer divs (32px) between sidebar button groups, no line — user confirmed this looks good. Don't re-attempt the same approaches if this comes up again; if the user wants another go, it probably needs a genuinely different technique, not a variation on padding/margin/height.
- **Sidebar dirty marker (●) is gone and hasn't been restored.** It used to sit next to the workfile name in a title line removed earlier this session (the file name itself wasn't useful — the red description badge at the top of the main content area is the real "what am I working on" signal, per the user). Nowhere currently shows "unsaved changes" at a glance in the sidebar. Not raised again after being flagged once — treat as accepted unless the user brings it up.
- **Sidebar/main CSS spacing is "good enough," not chased to perfection.** `core/ui/common/layout_css.py` handles top padding and the sidebar's `stSidebarHeader`/`stLogoSpacer`/`stSidebarUserContent`/inter-element gap. Some of it visibly worked, some didn't fully resolve — user explicitly said they're okay with the remainder.

## Worth remembering for any future UI/CSS work

**Process-restart gotcha.** The user's `.bat` starts a real background Streamlit server in a command prompt window; closing the browser tab does not stop it. Several "no change" reports this session turned out to be stale-server false negatives, resolved only once every leftover `python.exe`/command-prompt window was killed via Task Manager before rerunning. If a CSS/code change ever appears to have no effect, check this before concluding the change itself is wrong.

## Secondary, lower priority

- **Real data-quality gap, not a ChartGen bug:** some submissions in the underlying ics database have no matching organisation at all — caught correctly by the unmapped-organisation warning. User is investigating separately; no action needed from this side unless asked.
- No live batch-run test yet for: Period Range / Convert Periods to Metrics (built previous session), the `format_modifier` number-formatting rule, or the placeholder-removal change (both built this session). Worth suggesting a real batch-run pass if the user has a natural gap.
- TimeSeries charts and the Charts sheet round-trip more broadly still haven't had a real batch-run test against a live workfile/template.
- Tweaks (reference lines, axis control, conditional colouring, hook architecture) remain not built.

## Carried forward, not urgent

- One-hop-only `soft_parents` resolution is a deliberate scope boundary, not a bug — revisit only once a genuine multi-level chain (more than two tables deep) is actually needed.
- Table-wide `chart_type_ref`/`metric_periods` validation on Excel upload — still deferred by the user from an earlier session; needs a fresh conversation about what "proper" validation means before scoping any build.
- Population-table Excel edits still have no validation (a removed `unit_id` can leave a dangling `soft_parents` reference) — same deferral as above.
