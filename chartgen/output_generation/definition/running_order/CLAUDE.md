# running_order

The Running Order is an ordered sequence of report content. `schema.py` owns the column list, the function names, the scope values, and the function groupings.

The functions: `create_ppt`, `set_default_populations`, `update_text`, `insert_chart`, `insert_table`, `insert_picture`, `insert_from_excel`, `open_excel`, `close_excel`, `empty_placeholder`, `save_ppt`, `save_pdf`.

Three scopes: `normal`, `batch_open`, `batch_close`.

Adding a function means an entry in `ALL_FUNCTIONS` here, membership of the right grouping set, and an entry in `assembly_engine.FUNCTION_MAP`.

## row_id is not stable

`row_id` renumbers whenever a row is inserted, deleted or reordered. An Overwrite leaves it unchanged; an Insert renumbers everything after the insertion point.

Never use `row_id` as a storage key, or as an anchor for anything that outlives the edit. Stat Tags anchor on `hex_id` for exactly this reason.

The Charts sheet tracks a selected row by `row_id` within a session, and clears its row-referencing state after any save so a fresh selection is required, rather than resolving a stale index.

## The sandbox field lists

`CHART_SANDBOX_FIELDS` and `TABLE_SANDBOX_FIELDS` are the round-trip field lists between a Running Order row and its authoring sandbox. Load and save both iterate the list rather than naming fields individually. Extending the round trip to a new field is a one-line addition here, not a change to the sync mechanism.

`chart_store_rows` mirrors `CHART_SANDBOX_FIELDS` exactly, plus its own id and description.

## The period fields are stored verbatim

`start_period`, `end_period` and `metric_periods` hold exactly what the user picked or typed, typically `period_label(period_id)` from a dropdown, or a bare id typed by hand.

`xlsx_writer.py` and `xlsx_reader.py` are pure passthrough for these three. No derivation on write, no parsing on read. Nothing anywhere rewrites, reconstructs or re-derives them.

Numeric extraction happens once, in `cut_resolution.prepare_chart_cut`. Do not add a second extraction point.

`row_ops.py` holds generic list operations only, with no knowledge of charts, shapes, or any particular caller.
