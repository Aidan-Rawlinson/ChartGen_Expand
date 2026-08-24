"""
Tests for output_generation/definition/running_order/row_ops.py

These three operations are how the Charts sheet and the Tables tab write
back into the Running Order, which is the document that defines an entire
report. The rules worth protecting come from two places.

ui/tabs/charts_tab/sheet.py: "Rows are referenced by row_id, never by list
position. row_id survives an Overwrite but not an Insert, which is why
sandbox state referencing rows is cleared after every save." So the
renumbering behaviour is not an implementation detail; the calling code is
built around it.

row_ops.py's own docstring on Overwrite: "Every other column on that row
(position, scope, notes, etc.) is left untouched." A save from the Charts
sheet must not quietly wipe the slide position or the notes a user typed on
the Running Order tab.
"""

from chartgen.output_generation.definition.running_order.row_ops import (
    append_content_row_above_footer,
    insert_new_row,
    overwrite_row_fields,
    renumber_row_ids,
)
from chartgen.output_generation.definition.running_order.schema import COLUMNS


# ---------------------------------------------------------------------------
# renumber_row_ids
# ---------------------------------------------------------------------------

def test_row_ids_are_renumbered_sequentially_from_one():
    rows = [{"row_id": 99}, {"row_id": 7}, {"row_id": 3}]
    renumber_row_ids(rows)
    assert [r["row_id"] for r in rows] == [1, 2, 3]


def test_renumbering_follows_list_order_not_the_previous_ids():
    rows = [{"row_id": 3, "tag": "c"}, {"row_id": 1, "tag": "a"}]
    renumber_row_ids(rows)
    assert [(r["row_id"], r["tag"]) for r in rows] == [(1, "c"), (2, "a")]


def test_renumbering_an_empty_running_order_does_nothing():
    rows = []
    renumber_row_ids(rows)
    assert rows == []


# ---------------------------------------------------------------------------
# overwrite_row_fields
# ---------------------------------------------------------------------------

def test_overwrite_replaces_only_the_fields_it_was_given(running_order_rows):
    overwrite_row_fields(running_order_rows, 1, {"base_chart_name": "box_whisker"})
    assert running_order_rows[1]["base_chart_name"] == "box_whisker"


def test_overwrite_leaves_every_other_column_untouched(running_order_rows):
    """
    The documented promise. A Charts sheet save sends only the nine
    CHART_SANDBOX_FIELDS, so anything else on the row belongs to the user
    and must survive.
    """
    before = dict(running_order_rows[1])
    overwrite_row_fields(running_order_rows, 1, {"base_chart_name": "box_whisker"})
    after = running_order_rows[1]

    for column, value in before.items():
        if column != "base_chart_name":
            assert after[column] == value, column


def test_overwrite_does_not_change_the_row_id(running_order_rows):
    """
    Why the Charts sheet can keep a row bound across an Overwrite but not
    across an Insert.
    """
    overwrite_row_fields(running_order_rows, 1, {"base_chart_name": "box_whisker"})
    assert running_order_rows[1]["row_id"] == 2


def test_overwrite_does_not_change_the_length_of_the_running_order(running_order_rows):
    overwrite_row_fields(running_order_rows, 1, {"base_chart_name": "box_whisker"})
    assert len(running_order_rows) == 5


# ---------------------------------------------------------------------------
# insert_new_row
# ---------------------------------------------------------------------------

def test_inserting_above_puts_the_new_row_before_the_target(running_order_rows):
    new_idx = insert_new_row(running_order_rows, 2, {"notes": "inserted"}, "above")
    assert new_idx == 2
    assert running_order_rows[2]["notes"] == "inserted"
    assert running_order_rows[3]["notes"] == "second chart"


def test_inserting_below_puts_the_new_row_after_the_target(running_order_rows):
    new_idx = insert_new_row(running_order_rows, 2, {"notes": "inserted"}, "below")
    assert new_idx == 3
    assert running_order_rows[2]["notes"] == "second chart"
    assert running_order_rows[3]["notes"] == "inserted"


def test_the_returned_index_is_where_the_new_row_actually_is(running_order_rows):
    """
    The caller uses this to rebind its own selection, so an off-by-one here
    would rebind the sandbox to a neighbouring row.
    """
    for position in ["above", "below"]:
        rows = [dict(r) for r in running_order_rows]
        new_idx = insert_new_row(rows, 2, {"notes": "marker"}, position)
        assert rows[new_idx]["notes"] == "marker"


def test_an_inserted_row_copies_structural_columns_from_its_target(running_order_rows):
    """
    Documented: "copied from rows[target_index] for every column not in
    field_values". A chart inserted next to another should land on the same
    slide, not on no slide at all.
    """
    insert_new_row(running_order_rows, 2, {"base_chart_name": "dot_matrix"}, "below")
    inserted = running_order_rows[3]
    assert inserted["slide_index"] == "2"
    assert inserted["function"] == "insert_chart"
    assert inserted["base_chart_name"] == "dot_matrix"


def test_an_inserted_row_has_every_column_in_the_schema(running_order_rows):
    """
    A row missing a column would raise on the CSV write at Save, which is
    the worst possible moment to find out.
    """
    insert_new_row(running_order_rows, 2, {"notes": "inserted"}, "below")
    assert set(running_order_rows[3]) == set(COLUMNS)


def test_row_ids_are_renumbered_across_the_whole_list_after_an_insert(running_order_rows):
    insert_new_row(running_order_rows, 1, {"notes": "inserted"}, "above")
    assert [r["row_id"] for r in running_order_rows] == [1, 2, 3, 4, 5, 6]


def test_an_insert_shifts_the_row_ids_of_everything_below_it(running_order_rows):
    """
    The reason the Charts sheet clears its row references after a save. The
    save_ppt row was id 4 and is now id 5, so a held reference to "row 4"
    would now point at a different row.
    """
    insert_new_row(running_order_rows, 1, {"notes": "inserted"}, "above")
    save_ppt_row = next(r for r in running_order_rows if r["function"] == "save_ppt")
    assert save_ppt_row["row_id"] == 5


# ---------------------------------------------------------------------------
# append_content_row_above_footer
# ---------------------------------------------------------------------------

def test_a_new_content_row_lands_immediately_above_save_ppt(running_order_rows):
    """
    Content belongs in the per-report section, before the save footer.
    Below save_ppt it would be written after the file had already been
    saved, and would silently never appear in the report.
    """
    new_idx = append_content_row_above_footer(running_order_rows, {"function": "insert_table"})
    assert new_idx == 3
    assert running_order_rows[3]["function"] == "insert_table"
    assert running_order_rows[4]["function"] == "save_ppt"


def test_a_new_content_row_is_enabled_and_normal_scope_by_default(running_order_rows):
    """
    A table created in the UI should appear in the next report without the
    user having to enable it, and must not be batch-scoped.
    """
    append_content_row_above_footer(running_order_rows, {"function": "insert_table"})
    created = running_order_rows[3]
    assert created["enabled"] == 1
    assert created["scope"] == "normal"


def test_a_new_content_row_starts_blank_apart_from_what_was_given(running_order_rows):
    """
    Unlike insert_new_row there is no neighbouring row to copy from, so
    nothing should be inherited by accident. In particular no slide_index:
    the row deliberately has no position yet.
    """
    append_content_row_above_footer(running_order_rows, {"function": "insert_table", "table_id": "1"})
    created = running_order_rows[3]
    assert created["slide_index"] == ""
    assert created["base_chart_name"] == ""
    assert created["notes"] == ""


def test_a_new_content_row_has_every_column_in_the_schema(running_order_rows):
    append_content_row_above_footer(running_order_rows, {"function": "insert_table"})
    assert set(running_order_rows[3]) == set(COLUMNS)


def test_row_ids_are_renumbered_after_appending_a_content_row(running_order_rows):
    append_content_row_above_footer(running_order_rows, {"function": "insert_table"})
    assert [r["row_id"] for r in running_order_rows] == [1, 2, 3, 4, 5, 6]


def test_the_first_save_ppt_is_the_anchor_when_there_is_more_than_one():
    """
    Recording the documented behaviour: the insertion point is the first
    save_ppt, so content lands in the first report's section.
    """
    rows = [
        {"row_id": 1, "function": "create_ppt"},
        {"row_id": 2, "function": "save_ppt"},
        {"row_id": 3, "function": "create_ppt"},
        {"row_id": 4, "function": "save_ppt"},
    ]
    new_idx = append_content_row_above_footer(rows, {"function": "insert_table"})
    assert new_idx == 1


def test_a_running_order_with_no_save_ppt_appends_at_the_end():
    """
    The documented fallback. Should not happen with a generated Running
    Order, but must not raise or lose the row if it does.
    """
    rows = [{"row_id": 1, "function": "create_ppt"}]
    new_idx = append_content_row_above_footer(rows, {"function": "insert_table"})
    assert new_idx == 1
    assert rows[1]["function"] == "insert_table"
