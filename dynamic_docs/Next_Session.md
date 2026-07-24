<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

- **Docs re-upload — done.** Confirmed re-uploaded to Claude Desktop Project Files.

## This session's work, for context

- **Three-scenario yellow box resolution** replaces the old "must be fully inside a placeholder" rule (Architecture Decision 13): fully contained (matched to placeholder), no overlap (free-floating, box's own position/size used, named after its own shape name), partial overlap (ambiguous, left alone, warned). Unrecognised content now warns instead of silently stripping; a summary warning line is prepended whenever any warning exists.
- **Theme-referenced fill colour resolution** (Architecture Decision 14) — `_get_shape_fill_rgb` now also resolves a shape's "Shape Styles" `fillRef` (a theme colour pointer, not a literal fill) through the slide's colour map and the theme's colour scheme. Found and fixed via live testing against a real uploaded template, which had most of its yellow boxes styled this way.
- **1mm containment tolerance** — `_fully_contained` now allows 36,000 EMU of drift per edge, absorbing sub-visible PowerPoint copy/paste rounding (observed: a genuine 1 EMU discrepancy) that was misclassifying a contained box as a partial overlap.
- **Outputs tab slider crash** — `st.slider` with `min_value == max_value == 1` whenever `remaining <= 1` (e.g. before any fetch). Fixed by showing a plain batch-size label instead of a slider in that case, keeping Reset queue always visible.
- All four fixes this session were driven by live testing against a real uploaded `.pptx`, not just code review — worth continuing that pattern for any future detection-logic work.
