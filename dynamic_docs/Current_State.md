<!-- Purpose: A snapshot of where the project stands right now -- what works, what is in progress, what is broken. Rewritten by Claude each session. -->

> **CLAUDE — READ THIS FIRST, EVERY SESSION.** This block is for you, not the user. Nobody ever reads this document. Do not soften it, do not let it drift to the bottom, and do not let a future rewrite of this file drop it.
>
> **Phase: Expansion.** The major refactor is complete. `code_base` and the five governed documents describe a stable, refactored base. This phase is about building new functionality on top of that base — which means structure and logic in both the code and the documents SHOULD be expected to change, repeatedly, as each new feature lands. Do not treat the current structure as fixed or sacred. Do not read a structural mismatch between what's documented and what's proposed as an error to flag cautiously — during this phase, it's the expected shape of the work. Ground truth discipline (Maintenance Guide Section 4) still applies fully: check actual code before updating docs, present-tense only. What changes is your posture going in — expect churn, don't resist it.

## Status: This session reworked the yellow-box/placeholder detection model and fixed two real bugs surfaced by testing it against a live template. The old "must sit fully inside a placeholder" rule is gone, replaced with a three-outcome resolution (contained / free-floating / ambiguous overlap). Testing then found the colour detector missed a whole class of real-world yellow boxes, and a 1 EMU rounding artefact was misclassifying genuinely-contained boxes — both are now fixed and verified against the user's actual test file. A separate, unrelated Outputs tab crash was also found and fixed along the way.

### What works (built/fixed this session)

- **Three-scenario yellow box resolution (`template_reader.read_template`, Architecture Decision 13).** Replaces the old placeholder-containment-only rule, since PowerPoint placeholders can only be added via Slide Master/Layout — not drawn onto an existing slide — making the old rule unworkable for ad hoc content addition. Each detected yellow box now resolves into one of three outcomes:
  1. **Fully contained** in a placeholder — matched to it, placeholder's own position/size used (as before).
  2. **No overlap** with any placeholder — free-floating; the box's own position/size are used directly, and it's carried through as its own `PlaceholderInfo`, named after its own PowerPoint shape name.
  3. **Partial overlap**, short of full containment — ambiguous; left entirely alone (not classified, not added to the Running Order, not removed from the cleaned template), warning raised.
  - Unrecognised yellow box content (matches none of chart/picture/Excel) is now warned rather than silently stripped.
  - Any template read producing at least one warning gets a summary line prepended ("One or more yellow boxes could not be processed").

- **Theme-referenced fill colour resolution (Architecture Decision 14).** Testing against a real template (`Presentation_Example_2_Projects.pptx`) found that most of its yellow boxes were invisible to detection entirely — they get their colour via PowerPoint's "Shape Styles" gallery (`<p:style><a:fillRef><a:schemeClr val="accent4"/></a:fillRef>`), which stores no literal colour on the shape at all, only a pointer into the theme. `_get_shape_fill_rgb` now resolves, in order: explicit literal fill → explicit theme-colour fill on the shape → the shape's style `fillRef`, each theme reference resolved through the slide's colour map (respecting a slide-level `clrMapOvr` override, or falling back to the slide master's own `clrMap`) and the theme's `clrScheme`, walking the full slide → layout → master → theme chain. Verified against the real file: all 5 previously-invisible chart boxes are now correctly detected and classified.
  - Deliberate simplification: doesn't model `fillStyleLst` shade/gradient variants on a `fillRef` — uses the base scheme colour unmodified. Fine for yellow detection's tolerant HSV thresholds; not a general-purpose theme-colour renderer.

- **1mm containment tolerance (`_fully_contained`, part of Decision 14).** Same test file showed a box whose right edge was exactly 1 EMU (≈0.000001 inch) outside its placeholder's — pure PowerPoint copy/paste rounding noise, not a real design gap — being misclassified as "partial overlap." Added a 36,000 EMU (1mm) tolerance on each edge of the containment check. Verified: all 10 chart boxes across the paired-box slides now match correctly; the only remaining warnings on that file are two genuinely-empty yellow boxes (no text at all), correctly flagged as unrecognised content.

- **Outputs tab batch-size slider crash fixed (`outputs_tab.py`).** `st.slider(min_value=1, max_value=min(50, max(remaining, 1)))` collapsed to `min_value == max_value == 1` whenever `remaining` was 0 or 1 (e.g. viewing Outputs before any fetch has run, when the master population table is still empty) — Streamlit raises in that case. Root cause of why this hadn't been hit before: any template with a real chart URL normally trips the pre-existing "unassigned chart type" setup check first (since `chart_type_ref` starts blank until a fetch resolves the shape), which blocks reaching the slider at all — this only surfaced because the specific test template had no chart URLs, only picture/Excel content. Fixed by showing a plain "Batch size: N" label instead of a slider whenever `remaining <= 1`; the Reset queue button now always renders regardless of which branch is taken (an earlier draft of the fix accidentally hid it in the `remaining <= 1` case — caught and corrected before finalising).

- **Documentation updated (mirror only, not yet re-uploaded).** Functional Spec §6.3/6.4 rewritten for the three-outcome model, theme-colour detection, and the 1mm tolerance; Feature List's yellow textbox row updated; Glossary gained "Free-floating yellow box" and updated "Placeholder"/"Yellow textbox convention" entries; Architecture gained Decision 13 (three-scenario resolution) and Decision 14 (theme-colour resolution + containment tolerance).

### Known gaps / not yet done (carried forward)

- **Docs not yet re-uploaded to Project Files** — mirror is ahead of what Claude Desktop shows; re-upload and confirm at next session start if not done before this close-down completes.
- Detection has only been verified against one real template. Not yet exercised: a slide-level `clrMapOvr` override in practice, a non-identity `clrMap` (rare), or a `fillRef` idx pointing at a shaded/gradient theme variant rather than a flat solid (deliberately unmodelled — see above).
- Not yet re-tested live: the chart-type default-population backfill and the Running Order `placeholder`-column removal from the previous session — still carried forward as an open verification item.
- Prototype-sharing plan (quick-start guide, sample templates, installer check) — still open, untouched this session.
- Guidance PDF and its build script exist only on SharePoint / a prior session's sandbox — not saved into the project folder.
- Sidebar divider line — abandoned, root cause never identified. Don't relitigate without a genuinely different technique.
- Sidebar/main CSS spacing — accepted as "good enough."
- Sidebar dirty marker (●) — dropped, not raised again since. Treat as accepted unless the user brings it up.
- Process-restart gotcha still applies: the `.bat`'s background Streamlit server survives closing the browser tab. Flag early in any UI/CSS session where changes appear not to take effect.
- Table-wide `chart_type_ref`/`metric_periods` validation on Excel upload — still deferred.
- Population-table Excel edits still unvalidated (dangling `soft_parents` possible) — same deferral.
- No live batch-run test yet for Period Range / Convert Periods to Metrics, TimeSeries charts, or the Charts sheet round-trip more broadly, against a real template.
- Tweaks (reference lines, axis control, conditional colouring, hook architecture) — not built.
- One-hop-only `soft_parents` resolution — deliberate scope boundary, not a bug.
- The per-row `ctx.log` mechanism has no consumer anywhere (noted previous session, still unactioned) — either give it a real consumer or strip the now-pointless message-building out of every Running Order function.

### Resolved / dropped this session

- Yellow box detection rule — from "must be fully inside a placeholder" to the three-outcome model (Decision 13).
- Theme-referenced ("Shape Styles") yellow box fills — from invisible to correctly detected (Decision 14).
- 1 EMU-scale copy/paste rounding — from misclassified as partial overlap to correctly treated as contained (1mm tolerance).
- Outputs tab crash when `remaining <= 1` — fixed.
