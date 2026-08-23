# infrastructure

Generic helpers. Nothing here knows about charts, tables, toolkits or the UI.

## Ids

`id_generation.py` issues base-36 ids from a persisted counter in `settings`. Each id space keeps its own counter key, so the spaces never interleave. `next_id` mutates `settings` in place; the caller marks the workfile dirty.

Counters are never recomputed from surviving rows.

A row imported from Excel with its own id already filled in does not advance the counter, which can put the counter behind ids in use. `chart_store.next_chart_store_id` resyncs to the true maximum before incrementing. `next_stat_tag` and `next_table_id` do not.

## Versioning

`version_compatibility.py` owns two independent version numbers against its own CSV: `software_id` for this build, and `file_version_written` for the `.cgw` structure this build writes. `file_versions_readable` lists what this build can open.

A workfile outside that list is refused at Open. No partial read, no migration. Extending compatibility means adding an id to the list.
