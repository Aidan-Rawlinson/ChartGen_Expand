<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

- **Guidance link URLs are still placeholders.** Every tab's "📖 Guidance" link currently points at `bbc.co.uk` for styling purposes. Whenever the user has the real per-tab guidance pages, swap them into `GUIDANCE_URLS` in `core/ui/common/guidance.py` — one line per tab, no other code change needed.

## Open decisions the user made this session, don't relitigate

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
