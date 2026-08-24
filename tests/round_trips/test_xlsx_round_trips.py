"""
Round-trip tests for the six Excel export/import pairs

ChartGen offers an Excel round trip on six different tables, so a user can
edit in a spreadsheet rather than in the interface. Each is a matched writer
and reader, and each is a place data can be silently mangled: openpyxl hands
back whatever type Excel decided a cell was, and a cell that goes out as text
can easily come back as a number.

Six pairs, in one file rather than six, because they are the same test asked
six times and reading them side by side is how you notice one behaving
differently from the others.

  running_order   xlsx_writer.write_xlsx            / xlsx_reader.read_xlsx
  output tables   grid_xlsx.write_output_table_xlsx / read_output_table_xlsx
  chart store     chart_store_xlsx.write_...        / read_chart_store_xlsx
  stat tags       stat_tags_xlsx.write_...          / read_stat_tags_xlsx
  population      population_table_xlsx.write_...   / read_population_table_xlsx
  manifest        manifest_table.write_manifest_xlsx / read_manifest_xlsx

The value here is narrow and worth being clear about. These check that what
goes out comes back. They do not check that the spreadsheet looks right, has
the right dropdowns, or is pleasant to edit. Only opening one in Excel shows
that.

Everything writes to pytest's tmp_path.
"""

from chartgen.acquisition.manifest_table.xlsx_reader import read_manifest_xlsx
from chartgen.acquisition.manifest_table.xlsx_writer import write_manifest_xlsx
from chartgen.output_generation.definition.running_order.xlsx_reader import (
    _period_cell_to_str,
    _restore_json_suffix,
    read_xlsx,
)
from chartgen.output_generation.definition.running_order.xlsx_writer import write_xlsx
from chartgen.output_generation.execution.charts.chart_store_xlsx import (
    assign_missing_chart_store_ids,
    read_chart_store_xlsx,
    write_chart_store_xlsx,
)
from chartgen.output_generation.execution.tables.grid_store import new_grid
from chartgen.output_generation.execution.tables.grid_xlsx import (
    read_output_table_xlsx,
    write_output_table_xlsx,
)
from chartgen.output_generation.execution.text.stat_tags_xlsx import (
    assign_missing_tags,
    read_stat_tags_xlsx,
    write_stat_tags_xlsx,
)
from chartgen.shared.infrastructure.population_table_xlsx import (
    read_population_table_xlsx,
    write_population_table_xlsx,
)
from chartgen.workfile.state.workfile_file import (
    CHART_STORE_FIELDNAMES,
    MANIFEST_FIELDNAMES,
    TEXT_STATS_FIELDNAMES,
)


def complete(fieldnames, **values):
    """A row with every column in the schema present, blank unless given."""
    row = {name: "" for name in fieldnames}
    row.update(values)
    return row


# ---------------------------------------------------------------------------
# The cell-coercion helpers, which is where Excel's typing actually bites
# ---------------------------------------------------------------------------

def test_a_bare_period_id_typed_into_excel_does_not_come_back_with_a_decimal_point():
    """
    The documented environment fact, not a hypothetical: Excel decides a
    cell holding "1338" is the number 1338, and str() on that gives
    "1338.0", which matches no period on any shape.
    """
    assert _period_cell_to_str(1338.0) == "1338"


def test_a_stored_period_string_comes_back_exactly_as_stored():
    """
    No parsing at read time. The label stays attached, because extraction
    happens only where a cut is resolved.
    """
    assert _period_cell_to_str("July 2025(1338)") == "July 2025(1338)"


def test_a_genuinely_fractional_number_keeps_its_decimals():
    assert _period_cell_to_str(13.5) == "13.5"


def test_an_empty_period_cell_reads_as_blank():
    assert _period_cell_to_str(None) == ""
    assert _period_cell_to_str("") == ""


def test_the_json_suffix_is_put_back_on_a_cache_file_reference():
    """
    The writer strips ".json" because the user types the bare hex id. The
    dict key needs it back.
    """
    assert _restore_json_suffix("aa") == "aa.json"


def test_a_cache_file_already_carrying_the_suffix_is_not_double_suffixed():
    assert _restore_json_suffix("aa.json") == "aa.json"


def test_a_blank_or_none_cache_file_is_left_alone():
    assert _restore_json_suffix("") == ""
    assert _restore_json_suffix("none") == "none"


# ---------------------------------------------------------------------------
# Running Order
# ---------------------------------------------------------------------------

def test_running_order_rows_survive_the_excel_round_trip(tmp_path, running_order_rows):
    path = str(tmp_path / "running_order.xlsx")
    write_xlsx(running_order_rows, path)
    read_back = read_xlsx(path)

    assert len(read_back) == len(running_order_rows)
    assert [r["function"] for r in read_back] == [r["function"] for r in running_order_rows]


def test_a_running_order_cache_file_reference_survives_the_round_trip(tmp_path, running_order_rows):
    """
    Stripped on write, restored on read. If the two ever disagreed, every
    chart row would come back pointing at nothing.
    """
    path = str(tmp_path / "running_order.xlsx")
    write_xlsx(running_order_rows, path)
    read_back = read_xlsx(path)

    chart_rows = [r for r in read_back if r["function"] == "insert_chart"]
    assert [r["cache_file"] for r in chart_rows] == ["aa.json", "bb.json"]


def test_a_running_order_stored_period_is_not_rewritten_by_the_round_trip(tmp_path):
    """
    The root CLAUDE.md rule, at the boundary most likely to break it.
    """
    rows = [{"row_id": 1, "enabled": 1, "scope": "normal", "function": "insert_chart",
             "cache_file": "aa.json", "start_period": "July 2025(1338)",
             "metric_periods": "July 2025(1338)^August 2025(1339)"}]
    path = str(tmp_path / "running_order.xlsx")
    write_xlsx(rows, path)
    read_back = read_xlsx(path)

    assert read_back[0]["start_period"] == "July 2025(1338)"
    assert read_back[0]["metric_periods"] == "July 2025(1338)^August 2025(1339)"


def test_a_disabled_running_order_row_comes_back_disabled(tmp_path, running_order_rows):
    running_order_rows[2]["enabled"] = 0
    path = str(tmp_path / "running_order.xlsx")
    write_xlsx(running_order_rows, path)
    read_back = read_xlsx(path)
    assert str(read_back[2]["enabled"]).strip() in ("0", "False")


def test_an_empty_running_order_writes_and_reads_without_raising(tmp_path):
    path = str(tmp_path / "empty.xlsx")
    write_xlsx([], path)
    assert read_xlsx(path) == []


# ---------------------------------------------------------------------------
# Output Table grids
# ---------------------------------------------------------------------------

def test_an_output_table_grid_survives_the_excel_round_trip(tmp_path):
    grid = new_grid("t1", 2, 2)
    grid[1]["c1"] = "Heading"
    grid[2]["c2"] = "Body text"

    path = str(tmp_path / "grid.xlsx")
    write_output_table_xlsx(grid, [], path)
    read_back = read_output_table_xlsx(path)

    assert read_back == grid


def test_a_grid_s_stat_tag_and_chart_markers_survive_untouched(tmp_path):
    """
    "[T1]" and "{C1}" are resolved at render time, so the round trip must
    not interpret or reformat them.
    """
    grid = new_grid("t1", 2, 2)
    grid[1]["c1"] = "[T1]"
    grid[2]["c1"] = "{C1}"

    path = str(tmp_path / "grid.xlsx")
    write_output_table_xlsx(grid, [], path)
    read_back = read_output_table_xlsx(path)

    assert read_back[1]["c1"] == "[T1]"
    assert read_back[2]["c1"] == "{C1}"


def test_a_grid_s_percentage_sizes_keep_their_two_decimal_places(tmp_path):
    """
    These are read back with float(), so "50.00" arriving as 50 would still
    work, but the stored text should not quietly change either.
    """
    grid = new_grid("t1", 2, 2)
    path = str(tmp_path / "grid.xlsx")
    write_output_table_xlsx(grid, [], path)
    read_back = read_output_table_xlsx(path)
    assert read_back[0]["c1"] == "50.00"


def test_a_line_break_marker_typed_in_excel_survives_as_typed(tmp_path):
    """
    "<br>" becomes a real newline in resolve.py, not here. The round trip
    must leave it alone.
    """
    grid = new_grid("t1", 1, 1)
    grid[1]["c1"] = "First line<br>Second line"

    path = str(tmp_path / "grid.xlsx")
    write_output_table_xlsx(grid, [], path)
    assert read_output_table_xlsx(path)[1]["c1"] == "First line<br>Second line"


# ---------------------------------------------------------------------------
# Chart Store
# ---------------------------------------------------------------------------

def test_chart_store_rows_survive_the_excel_round_trip(tmp_path):
    rows = [
        complete(CHART_STORE_FIELDNAMES, chart_store_id="C1", base_chart_name="dot_strip",
                 cache_file="aa.json", populations="All^Selected",
                 width_emu="1000000", height_emu="500000", description="A stored chart"),
        complete(CHART_STORE_FIELDNAMES, chart_store_id="C2", base_chart_name="box_whisker",
                 cache_file="bb.json", populations="All"),
    ]
    path = str(tmp_path / "chart_store.xlsx")
    write_chart_store_xlsx(rows, path)
    assert read_chart_store_xlsx(path) == rows


def test_a_blank_chart_store_row_is_skipped_rather_than_imported(tmp_path):
    """
    A user deleting a row's contents in Excel but leaving the row there
    should not create an empty Chart Store entry.
    """
    rows = [complete(CHART_STORE_FIELDNAMES, chart_store_id="C1", base_chart_name="dot_strip")]
    path = str(tmp_path / "chart_store.xlsx")
    write_chart_store_xlsx(rows + [complete(CHART_STORE_FIELDNAMES)], path)
    assert len(read_chart_store_xlsx(path)) == 1


def test_a_chart_store_row_with_no_id_is_issued_one():
    """
    Documented: a blank id is filled in rather than left blank, because a
    blank id can never be referenced by a "{Cn}" marker.
    """
    rows = [complete(CHART_STORE_FIELDNAMES, chart_store_id="", base_chart_name="dot_strip")]
    assigned = assign_missing_chart_store_ids(rows, {})
    assert assigned[0]["chart_store_id"] != ""


def test_a_freshly_issued_chart_store_id_does_not_collide_with_one_in_the_upload():
    """
    The documented reason next_chart_store_id resyncs: a row uploaded with
    its own id never advanced the counter, so without the resync a new id
    could duplicate it. A duplicate would make a "{Cn}" marker ambiguous.
    """
    rows = [
        complete(CHART_STORE_FIELDNAMES, chart_store_id="C1"),
        complete(CHART_STORE_FIELDNAMES, chart_store_id="C2"),
        complete(CHART_STORE_FIELDNAMES, chart_store_id=""),
    ]
    assigned = assign_missing_chart_store_ids(rows, {})
    ids = [r["chart_store_id"] for r in assigned]
    assert len(set(ids)) == 3


def test_two_blank_chart_store_rows_do_not_collide_with_each_other():
    rows = [
        complete(CHART_STORE_FIELDNAMES, chart_store_id=""),
        complete(CHART_STORE_FIELDNAMES, chart_store_id=""),
    ]
    assigned = assign_missing_chart_store_ids(rows, {})
    assert assigned[0]["chart_store_id"] != assigned[1]["chart_store_id"]


# ---------------------------------------------------------------------------
# Stat Tags
# ---------------------------------------------------------------------------

def test_stat_tag_rows_survive_the_excel_round_trip(tmp_path):
    rows = [
        complete(TEXT_STATS_FIELDNAMES, tag="T1", hex_id="aa", populations="All",
                 reference_id="Mn", description="Mean"),
        complete(TEXT_STATS_FIELDNAMES, tag="T2", hex_id="aa", populations="Selected",
                 reference_id="Md"),
    ]
    path = str(tmp_path / "stat_tags.xlsx")
    write_stat_tags_xlsx(rows, path)
    assert read_stat_tags_xlsx(path) == rows


def test_a_stat_tag_row_with_no_tag_is_issued_one():
    """
    Documented: "a blank tag can never be matched to any [tag] in a
    template, so leaving it blank would just silently create a dead row".
    """
    rows = [complete(TEXT_STATS_FIELDNAMES, tag="", hex_id="aa", reference_id="Mn")]
    assigned = assign_missing_tags(rows, {})
    assert assigned[0]["tag"] != ""


def test_a_stat_tag_s_stored_period_survives_the_round_trip(tmp_path):
    rows = [complete(TEXT_STATS_FIELDNAMES, tag="T1", hex_id="aa",
                     start_period="July 2025(1338)", reference_id="Mn")]
    path = str(tmp_path / "stat_tags.xlsx")
    write_stat_tags_xlsx(rows, path)
    assert read_stat_tags_xlsx(path)[0]["start_period"] == "July 2025(1338)"


# ---------------------------------------------------------------------------
# Population tables
# ---------------------------------------------------------------------------

def test_a_population_table_survives_the_excel_round_trip(tmp_path, unit_rows):
    path = str(tmp_path / "population.xlsx")
    write_population_table_xlsx("submissions_2026", unit_rows, path)
    read_back = read_population_table_xlsx(path)

    assert len(read_back) == len(unit_rows)
    assert [r["unit_id"] for r in read_back] == ["u1", "u2", "u3", "u4"]


def test_a_population_table_s_peer_group_column_keeps_its_brackets(tmp_path, unit_rows):
    """
    The "()" suffix is the whole signal that a column is a peer group.
    """
    path = str(tmp_path / "population.xlsx")
    write_population_table_xlsx("submissions_2026", unit_rows, path)
    read_back = read_population_table_xlsx(path)

    assert "Region()" in read_back[0]
    assert read_back[0]["Region()"] == "North"


def test_a_population_table_s_soft_parents_links_survive(tmp_path):
    """
    A mangled soft_parents cell would break the unit set on every chart in
    the workfile, and would look like nothing more than a text change.
    """
    rows = [{"unit_id": "u1", "unit_code": "A01", "unit_name": "Alpha",
             "soft_parents": "nhs_organisations:n1^n2|submissions_2025:s1"}]
    path = str(tmp_path / "population.xlsx")
    write_population_table_xlsx("submissions_2026", rows, path)
    read_back = read_population_table_xlsx(path)

    assert read_back[0]["soft_parents"] == "nhs_organisations:n1^n2|submissions_2025:s1"


def test_a_unit_id_that_looks_numeric_comes_back_as_text(tmp_path):
    """
    Unit ids are compared as strings throughout ChartGen. An id of "1"
    coming back as the number 1 would stop matching, and the unit would
    quietly drop out of every population layer.
    """
    rows = [{"unit_id": "1", "unit_code": "A01", "unit_name": "Alpha", "soft_parents": ""}]
    path = str(tmp_path / "population.xlsx")
    write_population_table_xlsx("submissions_2026", rows, path)
    read_back = read_population_table_xlsx(path)

    assert read_back[0]["unit_id"] == "1"
    assert isinstance(read_back[0]["unit_id"], str)


def test_a_blank_population_row_is_skipped(tmp_path, unit_rows):
    path = str(tmp_path / "population.xlsx")
    write_population_table_xlsx("submissions_2026", unit_rows + [{}], path)
    assert len(read_population_table_xlsx(path)) == len(unit_rows)


# ---------------------------------------------------------------------------
# Manifest table
# ---------------------------------------------------------------------------

def test_manifest_rows_survive_the_excel_round_trip(tmp_path):
    rows = [
        complete(MANIFEST_FIELDNAMES, chart_ref="1", hex_id="aa",
                 url="https://members.nhsbenchmarking.nhs.uk/outputs/6",
                 chart_title="Invented chart", database="nhs",
                 shape_type="NumericSeries", source="Direct Input", deleted="0"),
    ]
    path = str(tmp_path / "manifest.xlsx")
    write_manifest_xlsx(rows, path)
    read_back = read_manifest_xlsx(path)

    assert len(read_back) == 1
    assert read_back[0]["hex_id"] == "aa"
    assert read_back[0]["url"] == "https://members.nhsbenchmarking.nhs.uk/outputs/6"


def test_a_manifest_url_with_a_query_string_survives_intact(tmp_path):
    """
    The query string carries the chart's identity on both toolkits, so
    losing or truncating it would silently point the row at a different
    chart.
    """
    url = "https://members.nhsbenchmarking.nhs.uk/project/42/toolkit?a=6657&b=6658&reportId=420995"
    rows = [complete(MANIFEST_FIELDNAMES, chart_ref="1", hex_id="aa", url=url,
                     database="indicators", source="Direct Input", deleted="0")]
    path = str(tmp_path / "manifest.xlsx")
    write_manifest_xlsx(rows, path)
    assert read_manifest_xlsx(path)[0]["url"] == url
