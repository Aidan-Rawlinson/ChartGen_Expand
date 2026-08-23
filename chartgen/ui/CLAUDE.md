# ui

Streamlit only. Business logic belongs to the module that owns it, not here. A tab renders, collects input, and calls out.

## The two tab packages

`charts_tab/` and `output_tables_tab/` are packages, not modules. Each has a `sheet.py` holding the tab entry point and one module per section below it. Every other tab is still a single file.

Each package's `__init__.py` exports exactly two names, the render function and the pre-Save capture function, and those are the only two used from outside. Nothing outside a package imports one of its inner modules.

`sheet.py` is the order of the sheet. The sequence of section calls in it is load-bearing: Streamlit cannot change a widget already instantiated this pass, so a value has to be staged into a pending key before the widget it targets is created. Do not reorder those calls to make the file read better.

## Session state

Each tab prefixes its own session keys, and `session_state.clear_workfile_session_state` wipes them wholesale on every Open and Close so a freshly opened workfile never inherits another's in-progress state.

| Prefix | Owner |
|---|---|
| `cs_` | Charts sheet sandbox |
| `ot_` | Output Tables selection, shared by Edit Grid and Preview |
| `ots_` | Output Tables preview configuration, kept separate so Reset does not disturb the selection |
| `ro_` | Running Order tab |
| `ts_` | Text tab |

Sandbox values that should survive a Close are captured into a settings key as a JSON blob before every Save, and restored once per Open. Restoration re-validates every field against what is actually available at that point, so a deleted chart or a regenerated Running Order falls back cleanly.

## Percent is a widget-only unit

The Sizing controls on the Charts sheet and the Output Tables tab show percent of the shorter page dimension. That is the only place percent exists. It converts to and from EMU immediately on read and write, and never travels further. Nothing in session state, in a saved JSON blob, or in any render call holds a percentage.

The Sizing box shows the real converted value, however small or large. It does not substitute a plausible-looking default for a value it finds surprising. A stored size that converts to 0.03% displays as 0.03%, because that is what is stored. Anything that would silently write a different number into that box is a defect, not a safeguard: the box is a save-back surface, so a substituted value gets committed to the row on the next save.

The box therefore carries no upper bound. `st.number_input` raises if session state holds a value above its `max_value`, so a ceiling on the widget forces a clamp on the restore path, and the clamp is the defect. A user can consequently type a size that runs off the page. That is visible on the next preview and it is their choice.

A stored value that will not parse as a number at all is reported with `st.error`, and the session key is left unset so the ordinary starting value applies. Not `st.stop()`: the restore runs once per session, and the Reset control that clears a corrupted snapshot lives inside the tab, so halting the render would remove the only route out.

## Render scale

Both preview surfaces render at the inflated size and display at the real size via CSS, matching what the final report does. Both import `CHART_RENDER_SCALE` from `shared/infrastructure/render_scale.py` rather than defining their own. See `output_generation/execution/charts/base_charts/CLAUDE.md`.
