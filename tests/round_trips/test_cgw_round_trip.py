"""
Round-trip tests for the .cgw workfile format
(workfile/state/workfile_file.py)

The .cgw is the user's work. Everything they have built lives in it, it is
shared with colleagues through SharePoint, and there is no other copy. Silent
loss here is the worst failure ChartGen can have: the file still opens, so
nothing looks wrong until somebody notices their Chart Store is empty.

workfile/CLAUDE.md: "state/workfile_file.py owns the .cgw format and is the
only module that reads or writes the ZIP. Nothing else opens it." So this one
module is the whole surface, and a round trip through it is the whole test.

The main test below fills every one of WorkfileState's twelve payload fields,
saves, reopens and compares. That single test is what guards the format:
adding a thirteenth field without adding it to both save_workfile and
open_workfile is exactly the mistake that would lose data quietly, and it
would fail here.

Everything writes to pytest's tmp_path. No real workfile is touched.
"""

import zipfile

import pytest

from chartgen.output_generation.definition.running_order import COLUMNS
from chartgen.shared.infrastructure.version_compatibility import get_file_version_written
from chartgen.workfile.state.workfile_file import (
    CHART_STORE_FIELDNAMES,
    CUSTOM_CHART_FIELDNAMES,
    CUSTOM_TABLE_FIELDNAMES,
    MANIFEST_FIELDNAMES,
    OUTPUT_TABLE_FIELDNAMES,
    TEXT_STATS_FIELDNAMES,
    WorkfileState,
    new_workfile,
    open_workfile,
    read_workfile_info,
    save_workfile,
)

USERNAME = "test.user@example.invalid"


@pytest.fixture
def populated_state(tmp_path):
    """
    A WorkfileState with something in every field that gets persisted.

    Deliberately not minimal: the point is to notice a field that stops
    being saved, and a field left empty here would not notice.

    Rows are built from the real FIELDNAMES lists rather than a chosen
    subset, for two reasons. A column not in the schema raises on save, so
    inventing one here would test nothing but my own typing. And a column
    left out comes back as an empty string, because every row read out of a
    .cgw is read out of a CSV, which would make a like-for-like comparison
    impossible.

    Values are strings for the same reason: a .cgw stores text. enabled is
    the one exception, coerced back to 1/0 on read by coerce_row.
    """
    state = WorkfileState(
        workfile_path=str(tmp_path / "test.cgw"),
        workfile_name="test",
    )

    def row(fieldnames, **values):
        """A complete row: every column in the schema, blank unless given."""
        complete = {name: "" for name in fieldnames}
        complete.update(values)
        return complete

    state.settings = {"description": "Invented test workfile", "outputs_folder": "out",
                      "next_stat_tag": "3", "next_table_id": "2"}
    state.table_order = ["submissions_2026", "nhs_organisations"]
    state.tables = {
        "submissions_2026": [
            {"unit_id": "u1", "unit_code": "A01", "unit_name": "Alpha Trust",
             "soft_parents": "nhs_organisations:n1", "Region()": "North"},
            {"unit_id": "u2", "unit_code": "B02", "unit_name": "Bravo Trust",
             "soft_parents": "", "Region()": "South"},
        ],
        "nhs_organisations": [
            {"unit_id": "n1", "unit_code": "RX1", "unit_name": "Alpha Org", "soft_parents": ""},
        ],
    }
    state.running_order_rows = [
        row(COLUMNS, row_id="1", enabled=1, scope="normal", function="create_ppt"),
        row(COLUMNS, row_id="2", enabled=1, scope="normal", function="insert_chart",
            cache_file="aa.json", base_chart_name="ranked_column",
            populations="All^Selected", start_period="2024/25(p2)",
            width_emu="3780000", height_emu="2000000", tweaks="title=off"),
        row(COLUMNS, row_id="3", enabled=0, scope="normal", function="save_ppt"),
    ]
    state.manifest_rows = [
        row(MANIFEST_FIELDNAMES, chart_ref="1", hex_id="aa",
            url="https://members.nhsbenchmarking.nhs.uk/outputs/6",
            chart_title="Invented chart", database="nhs", shape_type="NumericSeries",
            source="Direct Input", deleted="0"),
    ]
    state.cache = {"aa.json": '{"shape_type": "NumericSeries", "units": []}'}
    state.text_stats_rows = [
        row(TEXT_STATS_FIELDNAMES, tag="T1", hex_id="aa", populations="All",
            reference_id="Mn", description="Mean for the selected unit"),
    ]
    state.chart_store_rows = [
        row(CHART_STORE_FIELDNAMES, chart_store_id="C1", cache_file="aa.json",
            base_chart_name="dot_strip", populations="All",
            width_emu="1000000", height_emu="500000", description="A stored chart"),
    ]
    state.output_table_rows = [
        row(OUTPUT_TABLE_FIELDNAMES, table_id="1", table_name="Invented table",
            rows="2", columns="2"),
    ]
    state.output_tables = {
        "1": [
            {"c0": "1", "c1": "50.00", "c2": "50.00"},
            {"c0": "50.00", "c1": "Heading", "c2": "[T1]"},
            {"c0": "50.00", "c1": "{C1}", "c2": "text"},
        ],
    }
    state.custom_chart_rows = [
        row(CUSTOM_CHART_FIELDNAMES, base_chart_name="my_chart", shape_type="NumericSeries",
            added_at="2026-01-01T00:00:00+00:00"),
    ]
    state.custom_chart_code = {"my_chart": "def my_chart(layers, **kw):\n    return None\n"}
    state.custom_table_rows = [
        row(CUSTOM_TABLE_FIELDNAMES, table_type_ref="my_table",
            added_at="2026-01-01T00:00:00+00:00"),
    ]
    state.custom_table_code = {"my_table": "def my_table(content, **kw):\n    return None\n"}
    state.template_pptx_bytes = b"PK\x03\x04 not really a pptx, but bytes are bytes"

    return state


def save_and_reopen(state):
    save_workfile(state, USERNAME)
    return open_workfile(state.workfile_path)


# ---------------------------------------------------------------------------
# The whole-format round trip
# ---------------------------------------------------------------------------

def test_a_fully_populated_workfile_survives_a_save_and_reopen(populated_state):
    """
    The test that guards the format. Every persisted field, compared after a
    real save to disk and a real reopen.
    """
    reopened = save_and_reopen(populated_state)

    assert reopened.table_order == populated_state.table_order
    assert reopened.tables == populated_state.tables
    assert reopened.running_order_rows == populated_state.running_order_rows
    assert reopened.manifest_rows == populated_state.manifest_rows
    assert reopened.cache == populated_state.cache
    assert reopened.text_stats_rows == populated_state.text_stats_rows
    assert reopened.chart_store_rows == populated_state.chart_store_rows
    assert reopened.output_table_rows == populated_state.output_table_rows
    assert reopened.output_tables == populated_state.output_tables
    assert reopened.custom_chart_rows == populated_state.custom_chart_rows
    assert reopened.custom_chart_code == populated_state.custom_chart_code
    assert reopened.custom_table_rows == populated_state.custom_table_rows
    assert reopened.custom_table_code == populated_state.custom_table_code
    assert reopened.template_pptx_bytes == populated_state.template_pptx_bytes


def test_the_settings_a_user_set_survive_a_save_and_reopen(populated_state):
    reopened = save_and_reopen(populated_state)
    assert reopened.settings["description"] == "Invented test workfile"
    assert reopened.settings["outputs_folder"] == "out"


def test_the_id_counters_survive_so_ids_are_never_reissued(populated_state):
    """
    If the counters were lost, the next session would start from 1 and hand
    out ids already in use, silently rebinding Stat Tags to the wrong data.
    """
    reopened = save_and_reopen(populated_state)
    assert reopened.settings["next_stat_tag"] == "3"
    assert reopened.settings["next_table_id"] == "2"


def test_saving_twice_in_a_row_changes_nothing(populated_state):
    """
    A save must be idempotent in content. If a second save altered the data,
    simply opening and saving a colleague's workfile would change it.
    """
    first = save_and_reopen(populated_state)
    second = save_and_reopen(first)

    assert second.tables == first.tables
    assert second.running_order_rows == first.running_order_rows
    assert second.output_tables == first.output_tables
    assert second.chart_store_rows == first.chart_store_rows
    assert second.custom_chart_code == first.custom_chart_code


# ---------------------------------------------------------------------------
# Individual pieces worth calling out
# ---------------------------------------------------------------------------

def test_several_population_tables_are_each_stored_separately(populated_state):
    reopened = save_and_reopen(populated_state)
    assert set(reopened.tables) == {"submissions_2026", "nhs_organisations"}
    assert len(reopened.tables["submissions_2026"]) == 2


def test_a_peer_group_column_keeps_its_bracketed_name(populated_state):
    """
    The "()" suffix is what marks a peer-group column. Losing it in the CSV
    round trip would stop every peer-group population resolving.
    """
    reopened = save_and_reopen(populated_state)
    assert "Region()" in reopened.tables["submissions_2026"][0]
    assert reopened.tables["submissions_2026"][0]["Region()"] == "North"


def test_a_soft_parents_link_survives_intact(populated_state):
    reopened = save_and_reopen(populated_state)
    assert reopened.tables["submissions_2026"][0]["soft_parents"] == "nhs_organisations:n1"


def test_a_stored_period_string_keeps_its_label_and_brackets(populated_state):
    """
    The root CLAUDE.md rule that stored values are never rewritten, checked
    across the boundary where it would be easiest to lose: a CSV write and
    read. "2024/25(p2)" must not come back as "p2".
    """
    reopened = save_and_reopen(populated_state)
    chart_row = next(r for r in reopened.running_order_rows if r["function"] == "insert_chart")
    assert chart_row["start_period"] == "2024/25(p2)"


def test_a_disabled_running_order_row_stays_disabled(populated_state):
    """
    enabled is coerced to 1/0 on read. A disabled row coming back enabled
    would silently add content to every report.
    """
    reopened = save_and_reopen(populated_state)
    assert reopened.running_order_rows[2]["enabled"] == 0
    assert reopened.running_order_rows[0]["enabled"] == 1


def test_an_output_table_grid_keeps_its_markers_untouched(populated_state):
    """
    "[T1]" is a Stat Tag and "{C1}" a chart component. Both are resolved at
    render time, so they must survive storage exactly as typed.
    """
    reopened = save_and_reopen(populated_state)
    grid = reopened.output_tables["1"]
    assert grid[1]["c2"] == "[T1]"
    assert grid[2]["c1"] == "{C1}"


def test_custom_chart_code_survives_as_source_text(populated_state):
    """
    Stored as a .py inside the archive rather than in a CSV cell, because a
    newline in a CSV cell is a different problem entirely.
    """
    reopened = save_and_reopen(populated_state)
    assert reopened.custom_chart_code["my_chart"].startswith("def my_chart")
    assert "\n" in reopened.custom_chart_code["my_chart"]


def test_the_cached_chart_data_survives_byte_for_byte(populated_state):
    reopened = save_and_reopen(populated_state)
    assert reopened.cache["aa.json"] == '{"shape_type": "NumericSeries", "units": []}'


# ---------------------------------------------------------------------------
# Session-only state, and the save metadata
# ---------------------------------------------------------------------------

def test_a_reopened_workfile_is_not_marked_as_unsaved(populated_state):
    """
    workfile/CLAUDE.md: "dirty and read_only are session-only and are not
    persisted." A freshly opened workfile showing unsaved changes would
    train the user to ignore the warning.
    """
    reopened = save_and_reopen(populated_state)
    assert reopened.dirty is False
    assert reopened.read_only is False


def test_saving_records_who_saved_it_and_when(populated_state):
    reopened = save_and_reopen(populated_state)
    assert reopened.last_saved_by == USERNAME
    assert reopened.last_saved_at != ""


def test_saving_stamps_the_file_version_this_build_writes(populated_state):
    """
    The version the compatibility gate reads at Open. If this were not
    stamped, the workfile would be refused by the very build that wrote it.
    """
    reopened = save_and_reopen(populated_state)
    assert reopened.file_version_id == get_file_version_written()


def test_saving_does_not_write_the_lock(populated_state):
    """
    Documented: save updates "last_saved_by/at but not lock fields". The
    lock is written on Open and cleared on Close, by separate functions.
    """
    reopened = save_and_reopen(populated_state)
    assert reopened.locked_by == ""
    assert reopened.locked_at == ""


def test_the_workfile_name_survives(populated_state):
    assert save_and_reopen(populated_state).workfile_name == "test"


# ---------------------------------------------------------------------------
# Save As, and a brand-new workfile
# ---------------------------------------------------------------------------

def test_saving_to_a_new_path_leaves_the_original_file_alone(populated_state, tmp_path):
    """
    Save As. The original has to remain exactly as it was, since the user
    may well be branching a colleague's workfile.
    """
    save_workfile(populated_state, USERNAME)
    original_bytes = open(tmp_path / "test.cgw", "rb").read()

    copy_path = str(tmp_path / "copy.cgw")
    save_workfile(populated_state, USERNAME, target_path=copy_path)

    assert open(tmp_path / "test.cgw", "rb").read() == original_bytes
    assert open_workfile(copy_path).tables == populated_state.tables


def test_saving_to_a_new_path_moves_the_session_onto_it(populated_state, tmp_path):
    copy_path = str(tmp_path / "copy.cgw")
    save_workfile(populated_state, USERNAME, target_path=copy_path)
    assert populated_state.workfile_path == copy_path


def test_a_brand_new_workfile_exists_on_disk_and_can_be_opened(tmp_path):
    """
    workfile/CLAUDE.md: new_workfile "makes a blank .cgw: file, description,
    settings scaffold. It has no knowledge that population tables exist".
    """
    path = str(tmp_path / "brand_new.cgw")
    state = new_workfile(path, "brand_new")

    assert state.dirty is True
    assert zipfile.is_zipfile(path)

    reopened = open_workfile(path)
    assert reopened.tables == {}
    assert reopened.running_order_rows == []


def test_the_workfile_info_can_be_read_without_opening_the_whole_file(populated_state):
    """
    read_workfile_info is what the Open dialog uses to show who holds the
    lock, before committing to a full read.
    """
    save_workfile(populated_state, USERNAME)
    info = read_workfile_info(populated_state.workfile_path)
    assert info["workfile_name"] == "test"
    assert info["last_saved_by"] == USERNAME
    assert info["file_version_id"] == get_file_version_written()
