# infrastructure

Generic helpers. Nothing here knows about charts, tables, toolkits or the UI.

## Ids

`id_generation.py` issues base-36 ids from a persisted counter in `settings`. Each id space keeps its own counter key, so the spaces never interleave. `next_id` mutates `settings` in place; the caller marks the workfile dirty.

Counters are never recomputed from surviving rows. The counter only ever advances.

**An id can arrive from the user as well as from the system.** Every id space has an Excel round trip, and a person editing that spreadsheet may type whatever ids suit them: `AB1, AB2, AB3` then `AC1, AC2, AC3` is a natural way to number tabular material. A row imported with its id already filled in never advances the counter, so the counter cannot be assumed to know about every id in use.

`next_unique_id` therefore **checks rather than infers**. It issues from the counter, skips any candidate already in the ids passed to it, and parses nothing, so an id typed by hand in any form at all is honoured. Comparison is case-insensitive, because a Stat Tag is matched in a template by its exact literal text and `ab1` beside a user's `AB1` would be two ids a person reads as one.

`ids_in_use` is a required argument on all three issuers (`next_stat_tag`, `next_table_id`, `next_chart_store_id`). A caller that cannot say what is in use cannot be given a guaranteed-unique id, and fails loudly rather than silently skipping the check. `next_table_id`'s callers must pass both the index rows and the grid store, since either can hold an id the counter never issued.

An earlier version instead decoded every id in use as base-36 and pushed the counter past the highest. That inferred uniqueness rather than checking it, and had two faults worth not reintroducing: an id it could not decode was silently ignored, and a decoded value such as `AC3` (13,395) was written into the counter, so every later id became a long string derived from someone else's naming scheme. It also recomputed the counter from surviving rows, contradicting the rule above.

The manifest's `hex_id` (`workfile_file.generate_hex_id`) has always worked the checking way: it picks at random and retries until the value is unused, including against deleted rows.

## Versioning

`version_compatibility.py` owns two independent version numbers against its own CSV: `software_id` for this build, and `file_version_written` for the `.cgw` structure this build writes. `file_versions_readable` lists what this build can open.

A workfile outside that list is refused at Open. No partial read, no migration. Extending compatibility means adding an id to the list.
