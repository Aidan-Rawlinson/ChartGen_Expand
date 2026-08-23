# pptx_com

`comtypes` holds its "COM is initialised" state at module level, not per thread, and Streamlit gives each script rerun a fresh thread. Every COM entry point needs its own explicit `CoInitialize` and `CoUninitialize` pair.

Attach to a running PowerPoint with `GetActiveObject`, never `CreateObject`, which starts a fresh empty instance instead of finding the one the user is looking at.

COM reports position and size in points. Convert by 12700 before returning anything, so every value surfaced is in the EMU the Running Order stores.

Read-only. Nothing here writes back to the presentation, the Running Order, or anything else.
