# acquisition

Two toolkit APIs, template reading, and the manifest table. Must not import `workfile.setup`, which is why population-table construction lives inside each toolkit package where `fetch.py` can call it directly.

The two toolkit packages must not import each other. Anything needing both sits outside both: `url_triage.py` and `fetch_dispatch.py`.

## URL triage

A chart URL is classified `"nhs"` or `"indicators"` by path shape alone, once, at manifest-row creation, before either toolkit's own URL parsing runs.

| Toolkit | Path |
|---|---|
| nhs | `/outputs/{id}` |
| indicators | `/project/{id}/toolkit` |

Both share the same front-end domain, so the path is the only reliable signal. From that point on the manifest row's `database` column is the source of truth. Do not re-derive it.

## Transformer output

A transformer returns a populated canonical data shape, with `population_table` and `metadata["source_url"]` stamped at fetch time. It never returns a partially built shape for someone else to finish.

One credential set and token authorises both APIs. `toolkit_indicators` imports `get_token` from `toolkit_nhs.api_client` rather than duplicating it.
