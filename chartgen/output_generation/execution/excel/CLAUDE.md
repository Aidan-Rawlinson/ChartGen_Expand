# excel

Drives Excel through COM. `comtypes` holds its "COM is initialised" state at module level, not per thread, and Streamlit gives each script rerun a fresh thread, so this needs its own explicit `CoInitialize` and `CoUninitialize` pair.

Close what you open, in a `finally`, regardless of what failed above it, and drop the COM references explicitly afterwards. A COM object still referenced past its Python scope leaves the process running.
