# shared

Imports nothing from `acquisition`, `output_generation` or `ui`. Anything that needs to be shared with `shared` moves here, with a re-export shim left behind if callers depend on the old location. `period_ids.py` and `value_formatting.py` both arrived this way.
