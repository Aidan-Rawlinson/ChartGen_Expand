"""
Tests for output_generation/execution/tables/grid_store.py

An Output Table's grid is one spreadsheet-shaped artefact where the header
row holds column widths, the first column holds row heights, and everything
else is content. The offsets are easy to get wrong by one, and a mistake
there mixes sizes into content or loses the first row of the table.

The rule that matters most is on resize_grid: "A row or column introduced by
growing the grid gets an even share... computed independently of the
survivors rather than recalculated against them, so growing the grid never
silently rewrites sizes already authored elsewhere on it." That is the root
CLAUDE.md rule "Stored values are never rewritten" applied to grids, and the
natural-looking alternative (redistribute everything to sum to 100%) would
break it.

validate_grid is advisory by design: "out-of-tolerance values are flagged,
never auto-corrected".
"""

import pytest

from chartgen.output_generation.execution.tables.grid_store import (
    DEFAULT_TABLE_COLUMNS,
    DEFAULT_TABLE_ROWS,
    SIZE_SUM_TOLERANCE,
    col_key,
    get_column_widths,
    get_content_grid,
    get_row_heights,
    grid_dimensions,
    new_grid,
    next_table_id,
    resize_grid,
    validate_grid,
)


# ---------------------------------------------------------------------------
# The column-naming convention
# ---------------------------------------------------------------------------

def test_columns_are_named_c_then_the_index():
    """
    grid_xlsx.py reuses col_key so the two cannot drift. If this changed,
    every existing grid in every saved workfile would stop being readable.
    """
    assert col_key(0) == "c0"
    assert col_key(3) == "c3"


# ---------------------------------------------------------------------------
# new_grid
# ---------------------------------------------------------------------------

def test_a_new_grid_has_one_extra_row_and_column_for_the_sizes():
    grid = new_grid("t1", 3, 2)
    assert len(grid) == 4                # 3 content rows plus the header
    assert len(grid[0]) == 3             # 2 content columns plus the corner


def test_the_corner_cell_holds_the_table_id():
    assert new_grid("t7", 3, 2)[0]["c0"] == "t7"


def test_a_new_grid_starts_with_equal_column_widths_summing_to_about_one_hundred():
    widths = get_column_widths(new_grid("t1", 3, 4))
    assert widths == [25.0, 25.0, 25.0, 25.0]


def test_a_new_grid_starts_with_equal_row_heights():
    heights = get_row_heights(new_grid("t1", 4, 2))
    assert heights == [25.0, 25.0, 25.0, 25.0]


def test_rounding_drift_on_an_awkward_count_is_accepted_not_corrected():
    """
    Documented: "Rounding drift against an exact 100.00 total is accepted,
    not corrected." Three columns cannot divide 100 evenly, and forcing the
    last one to absorb the remainder would make it a different width from
    its neighbours for no visible reason.
    """
    widths = get_column_widths(new_grid("t1", 2, 3))
    assert widths == [33.33, 33.33, 33.33]
    assert sum(widths) != 100.0


def test_a_new_grid_has_blank_content_cells():
    grid = new_grid("t1", 2, 2)
    assert get_content_grid(grid) == [["", ""], ["", ""]]


def test_the_default_size_is_seven_by_four():
    """
    Documented as fixed: "Every Output Table starts at this size, whatever
    created it. There is no user-configurable size at creation."
    """
    assert (DEFAULT_TABLE_ROWS, DEFAULT_TABLE_COLUMNS) == (7, 4)


# ---------------------------------------------------------------------------
# Reading a grid back
# ---------------------------------------------------------------------------

def test_dimensions_exclude_the_size_row_and_column():
    assert grid_dimensions(new_grid("t1", 5, 3)) == (5, 3)


def test_dimensions_of_an_empty_grid_are_zero():
    assert grid_dimensions([]) == (0, 0)


def test_content_is_read_from_inside_the_size_row_and_column():
    """
    The off-by-one that would matter: reading from row 0 would return the
    column widths as if they were content.
    """
    grid = new_grid("t1", 2, 2)
    grid[1]["c1"] = "top left"
    grid[2]["c2"] = "bottom right"
    assert get_content_grid(grid) == [["top left", ""], ["", "bottom right"]]


def test_an_unparsable_width_reads_as_zero_rather_than_raising():
    """
    These cells are hand-editable through the Excel round-trip, so a
    non-numeric value will happen. It must not take down the render.
    """
    grid = new_grid("t1", 1, 2)
    grid[0]["c1"] = "wide-ish"
    assert get_column_widths(grid) == [0.0, 50.0]


def test_an_unparsable_height_reads_as_zero_rather_than_raising():
    grid = new_grid("t1", 2, 1)
    grid[1]["c0"] = ""
    assert get_row_heights(grid) == [0.0, 50.0]


def test_reading_an_empty_grid_gives_empty_lists():
    assert get_column_widths([]) == []
    assert get_row_heights([]) == []
    assert get_content_grid([]) == []


# ---------------------------------------------------------------------------
# validate_grid: advisory only
# ---------------------------------------------------------------------------

def test_a_fresh_grid_validates_cleanly():
    assert validate_grid(new_grid("t1", 4, 4)) == []


def test_widths_that_do_not_sum_to_one_hundred_are_flagged():
    grid = new_grid("t1", 2, 2)
    grid[0]["c1"] = "10.00"
    warnings = validate_grid(grid)
    assert len(warnings) == 1
    assert "Column widths" in warnings[0]


def test_heights_that_do_not_sum_to_one_hundred_are_flagged():
    grid = new_grid("t1", 2, 2)
    grid[1]["c0"] = "10.00"
    warnings = validate_grid(grid)
    assert len(warnings) == 1
    assert "Row heights" in warnings[0]


def test_widths_and_heights_are_checked_independently():
    """
    Two separate warnings, so the message tells the user which axis to fix.
    """
    grid = new_grid("t1", 2, 2)
    grid[0]["c1"] = "10.00"
    grid[1]["c0"] = "10.00"
    assert len(validate_grid(grid)) == 2


def test_validation_never_changes_the_grid_it_is_checking():
    """
    Advisory only. Silently correcting the user's widths here would be the
    "stored values are never rewritten" rule broken at the worst place,
    because Update writes the grid straight back to the workfile.
    """
    grid = new_grid("t1", 2, 2)
    grid[0]["c1"] = "10.00"
    before = [dict(r) for r in grid]
    validate_grid(grid)
    assert [dict(r) for r in grid] == before


def test_drift_inside_the_tolerance_is_not_flagged():
    """
    The tolerance exists because two-decimal percentages across an awkward
    count rarely total exactly 100.
    """
    grid = new_grid("t1", 3, 3)
    assert abs(sum(get_column_widths(grid)) - 100.0) <= SIZE_SUM_TOLERANCE
    assert validate_grid(grid) == []


# ---------------------------------------------------------------------------
# resize_grid
# ---------------------------------------------------------------------------

def test_growing_a_grid_keeps_the_content_already_in_it():
    grid = new_grid("t1", 2, 2)
    grid[1]["c1"] = "keep me"
    resized = resize_grid(grid, 4, 4, "t1")
    assert get_content_grid(resized)[0][0] == "keep me"


def test_shrinking_a_grid_keeps_the_content_still_inside_it():
    grid = new_grid("t1", 3, 3)
    grid[1]["c1"] = "survivor"
    resized = resize_grid(grid, 2, 2, "t1")
    assert get_content_grid(resized)[0][0] == "survivor"


def test_growing_a_grid_does_not_rewrite_widths_already_authored():
    """
    The rule this module is most at risk of losing. The user has deliberately
    made column 1 narrow and column 2 wide. Adding two more columns must
    leave those two exactly as they are, even though the total no longer
    resembles 100%.
    """
    grid = new_grid("t1", 2, 2)
    grid[0]["c1"] = "20.00"
    grid[0]["c2"] = "80.00"

    resized = resize_grid(grid, 2, 4, "t1")
    widths = get_column_widths(resized)

    assert widths[0] == 20.0
    assert widths[1] == 80.0


def test_growing_a_grid_does_not_rewrite_heights_already_authored():
    grid = new_grid("t1", 2, 2)
    grid[1]["c0"] = "10.00"
    grid[2]["c0"] = "90.00"

    resized = resize_grid(grid, 4, 2, "t1")
    heights = get_row_heights(resized)

    assert heights[0] == 10.0
    assert heights[1] == 90.0


def test_a_column_added_by_growing_gets_an_even_share_of_the_new_count():
    """
    Documented: the default for a new column is 100/count, computed
    independently of the survivors. With four columns that is 25.00, even
    though the two survivors here already account for 100%.
    """
    grid = new_grid("t1", 2, 2)
    grid[0]["c1"] = "20.00"
    grid[0]["c2"] = "80.00"

    widths = get_column_widths(resize_grid(grid, 2, 4, "t1"))
    assert widths[2] == 25.0
    assert widths[3] == 25.0


def test_a_resized_grid_has_the_size_it_was_asked_for():
    assert grid_dimensions(resize_grid(new_grid("t1", 2, 2), 5, 3, "t1")) == (5, 3)


def test_a_resized_grid_keeps_its_table_id_in_the_corner():
    assert resize_grid(new_grid("t1", 2, 2), 3, 3, "t1")[0]["c0"] == "t1"


def test_content_outside_a_shrunk_grid_is_dropped():
    """
    Recording the consequence plainly: shrinking loses content, because
    there is nowhere for it to go. Worth having stated somewhere.
    """
    grid = new_grid("t1", 3, 3)
    grid[3]["c3"] = "will be lost"
    resized = resize_grid(grid, 2, 2, "t1")
    assert "will be lost" not in [cell for row in get_content_grid(resized) for cell in row]


# ---------------------------------------------------------------------------
# next_table_id
# ---------------------------------------------------------------------------

def test_table_ids_carry_no_prefix():
    """Unlike a Stat Tag ("T3") or a Chart Store id ("C3")."""
    table_id = next_table_id({}, set())
    assert table_id.isalnum()
    assert not table_id.startswith(("T", "C"))


def test_the_first_table_id_in_a_fresh_workfile_is_short():
    assert next_table_id({}, set()) == "1"


def test_an_id_already_in_use_is_never_reissued():
    """
    A reissued table_id would point two Running Order rows at one grid, and
    an insert_table row at the wrong table.
    """
    ids_in_use = {"1", "2", "3"}
    assert next_table_id({}, ids_in_use) not in ids_in_use


def test_an_id_held_only_by_the_grid_store_still_blocks():
    """
    Callers must pass both the index rows and the grid store, because
    either can hold an id the counter never issued. This is the half that
    is easy to forget: a grid CSV inside the .cgw with no matching index
    row.
    """
    assert next_table_id({}, {"1"}) != "1"


def test_a_hand_typed_id_from_excel_is_respected():
    """
    "AB1" is not a value the counter would produce, and an implementation
    that decoded ids to find the highest would ignore it entirely. It still
    has to block that id.
    """
    ids_in_use = {"AB1", "AB2", "1"}
    issued = next_table_id({}, ids_in_use)
    assert issued.casefold() not in {i.casefold() for i in ids_in_use}


def test_ids_stay_short_after_a_user_numbers_tables_their_own_way():
    """
    Aidan's case, on the id space it was raised about. Numbering tables
    "AB1, AB2, AB3" then "AC1, AC2, AC3" is natural when building tabular
    material. The old implementation decoded "AC3" to 13,395 and wrote it
    into the counter, so every later table_id became a three-character
    string derived from that scheme.
    """
    ids_in_use = {"AB1", "AB2", "AB3", "AC1", "AC2", "AC3"}
    issued = next_table_id({}, ids_in_use)
    assert issued == "1"
    assert issued.casefold() not in {i.casefold() for i in ids_in_use}


def test_successive_table_ids_differ():
    settings = {}
    ids_in_use = set()
    issued = []
    for _ in range(3):
        new = next_table_id(settings, ids_in_use)
        ids_in_use.add(new)
        issued.append(new)

    assert issued == ["1", "2", "3"]


def test_the_table_id_space_has_its_own_counter():
    settings = {}
    next_table_id(settings, set())
    assert "next_table_id" in settings
    assert "next_stat_tag_id" not in settings


def test_the_ids_in_use_argument_is_required():
    with pytest.raises(TypeError):
        next_table_id({})
