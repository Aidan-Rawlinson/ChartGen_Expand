<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here — confirm docs re-upload, then verify this session's fixes live

- **Docs re-upload.** Functional Spec, Feature List, Architecture, and Glossary were all updated in the mirror this session. Confirm at session start whether the user has re-uploaded them to Claude Desktop Project Files yet; if not, that's the first thing to close out.
- **Yellow box detection.** Worth a fresh template read against `Presentation_Example_2_Projects.pptx` (or an equivalent real template) to reconfirm: all chart-URL boxes styled via the "Shape Styles" gallery now detect correctly, the paired left/right boxes on slides 5/6/8/9/11 both match their placeholders, and the two genuinely-empty boxes on slide 12 still correctly warn rather than silently vanish.
- **Outputs tab.** Confirm the batch-size control behaves correctly in both states — before any fetch (or with `remaining` at 0 or 1), and with a genuine range to slide across — and that Reset queue still works in both.

## Worth a scoping conversation, not urgent

- **Detection edge cases not yet exercised for real:** a slide-level `clrMapOvr` override, a non-identity `clrMap`, or a `fillRef` pointing at a shaded/gradient theme variant (idx > 1) rather than a flat solid. The last one is a deliberate simplification (Architecture Decision 14) — revisit only if a real template surfaces a shape whose visible colour doesn't match its theme's base scheme colour.

## Still open — prototype-sharing plan (untouched again this session)

Carried forward unchanged:

- **Quick-start guide** — a walkthrough of using the tool end-to-end against the sample PowerPoint templates. Not started.
- **Sample PowerPoint templates** — user's own task, two or three, varying complexity. Check status.
- **Installer check** — confirm the colleague can get ChartGen running on their own machine with their own login. Not started.
- Known-issues briefing explicitly out of scope, by user call — this is a look/feel/usability prototype, not an alpha or beta.

## This session's work, for context

- **Three-scenario yellow box resolution** replaces the old "must be fully inside a placeholder" rule (Architecture Decision 13): fully contained (matched to placeholder), no overlap (free-floating, box's own position/size used, named after its own shape name), partial overlap (ambiguous, left alone, warned). Unrecognised content now warns instead of silently stripping; a summary warning line is prepended whenever any warning exists.
- **Theme-referenced fill colour resolution** (Architecture Decision 14) — `_get_shape_fill_rgb` now also resolves a shape's "Shape Styles" `fillRef` (a theme colour pointer, not a literal fill) through the slide's colour map and the theme's colour scheme. Found and fixed via live testing against a real uploaded template, which had most of its yellow boxes styled this way.
- **1mm containment tolerance** — `_fully_contained` now allows 36,000 EMU of drift per edge, absorbing sub-visible PowerPoint copy/paste rounding (observed: a genuine 1 EMU discrepancy) that was misclassifying a contained box as a partial overlap.
- **Outputs tab slider crash** — `st.slider` with `min_value == max_value == 1` whenever `remaining <= 1` (e.g. before any fetch). Fixed by showing a plain batch-size label instead of a slider in that case, keeping Reset queue always visible.
- All four fixes this session were driven by live testing against a real uploaded `.pptx`, not just code review — worth continuing that pattern for any future detection-logic work.

## Open decisions from earlier sessions, don't relitigate

- **Sidebar divider line — dropped**, after extensive attempts, root cause never identified. Plain spacer divs in place, confirmed looking good. Don't re-attempt the same techniques if this comes up again.
- **Sidebar dirty marker (●) is gone**, not restored, not raised again since flagged once. Treat as accepted unless the user brings it up.
- **Sidebar/main CSS spacing is "good enough,"** not chased further.

## Worth remembering for any future UI/CSS work

**Process-restart gotcha.** The user's `.bat` starts a real background Streamlit server in a command prompt window; closing the browser tab does not stop it. If a CSS/code change ever appears to have no effect, check for a stale server (kill leftover `python.exe`/command-prompt windows via Task Manager) before concluding the change itself is wrong.

## Secondary, lower priority

- Not yet re-tested live (carried forward from before this session): the chart-type default-population backfill and the Running Order `placeholder`-column removal.
- No live batch-run test yet for: Period Range / Convert Periods to Metrics, TimeSeries charts, or the Charts sheet round-trip more broadly, against a real workfile/template.
- Tweaks (reference lines, axis control, conditional colouring, hook architecture) remain not built.

## Carried forward, not urgent

- One-hop-only `soft_parents` resolution is a deliberate scope boundary, not a bug.
- Table-wide `chart_type_ref`/`metric_periods` validation on Excel upload — still deferred; needs a fresh conversation about what "proper" validation means before scoping any build.
- Population-table Excel edits still have no validation (a removed `unit_id` can leave a dangling `soft_parents` reference) — same deferral as above.
- The per-row `ctx.log` mechanism has no consumer anywhere — either give it a real consumer or strip the now-pointless message-building out of every Running Order function.
