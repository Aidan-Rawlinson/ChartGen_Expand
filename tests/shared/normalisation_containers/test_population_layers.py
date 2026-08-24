"""
Tests for shared/normalisation_containers/population_layers.py

A populations string like "All^Selected^Region()" becomes the layers a chart
draws: the comparison scope first, then each subset. This is where a chart
gets its meaning, so a token that quietly disappears changes what the chart
is claiming without changing anything visible in the code.

The module states its guarantees outright, and they are what these tests
protect:

  "Every non-blank token produces exactly one layer, in order, and is never
  dropped. An unresolvable token still produces a layer with an empty unit
  set. Whether the reporting unit has data for this chart must never be why
  a token disappears."

  "The first token is the scope, the full set being compared. Each later
  token is an independent subset of that scope."

  "The scope may resolve empty. Every later token then resolves empty
  against it, rather than the layer list collapsing."

The last one is subtle and worth spelling out: an empty scope is a real
answer, not an error, and the layers still have to be there for the chart to
draw an empty comparison rather than nothing at all.
"""

from chartgen.shared.normalisation_containers.population_layers import (
    build_population_layers,
)


# ---------------------------------------------------------------------------
# Every token produces exactly one layer, in order
# ---------------------------------------------------------------------------

def test_a_blank_populations_string_produces_no_layers(numeric_series, unit_rows):
    """
    The only case that legitimately gives nothing back. A blank string means
    "inherit the Running Order default", handled by the caller.
    """
    assert build_population_layers(numeric_series, "", unit_rows, {"u1"}) == []
    assert build_population_layers(numeric_series, "   ", unit_rows, {"u1"}) == []


def test_one_token_produces_one_layer(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "All", unit_rows, {"u1"})
    assert len(layers) == 1


def test_three_tokens_produce_three_layers_in_the_order_given(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "All^Selected^Region(North)", unit_rows, {"u1"})
    assert [layer.population_label for layer in layers] == ["All", "Selected", "North"]


def test_empty_segments_between_carets_do_not_produce_layers(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "All^^Selected", unit_rows, {"u1"})
    assert [layer.population_label for layer in layers] == ["All", "Selected"]


def test_an_unrecognised_token_still_produces_a_layer(numeric_series, unit_rows):
    """
    The guarantee that matters most. Dropping the token would silently
    remove a series from the chart, and the chart would look perfectly
    reasonable without it.
    """
    layers = build_population_layers(numeric_series, "All^Nonsense", unit_rows, {"u1"})
    assert len(layers) == 2
    assert layers[1].population_label == "Nonsense"
    assert layers[1].units == []


def test_a_peer_group_matching_nobody_still_produces_a_layer(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "All^Region(Atlantis)", unit_rows, {"u1"})
    assert len(layers) == 2
    assert layers[1].units == []


def test_a_layer_with_no_units_is_still_a_usable_shape(numeric_series, unit_rows):
    """
    An empty layer has to carry its stats block per metric-series, or the
    chart cannot draw it as blank.
    """
    layers = build_population_layers(numeric_series, "Region(Atlantis)", unit_rows, {"u1"})
    empty = layers[0]
    assert empty.units == []
    assert len(empty.metric_stats) == len(numeric_series.metric_names)


# ---------------------------------------------------------------------------
# "All" and "Selected"
# ---------------------------------------------------------------------------

def test_all_resolves_to_every_unit_the_shape_holds(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "All", unit_rows, {"u1"})
    assert {u.unit_id for u in layers[0].units} == {"u1", "u2", "u3", "u4"}


def test_a_unit_with_no_data_is_still_part_of_all(numeric_series, unit_rows):
    """
    u4 has no value for this metric. It is still in the population, and the
    chart's "no data" count depends on it being there.
    """
    layers = build_population_layers(numeric_series, "All", unit_rows, {"u1"})
    assert "u4" in {u.unit_id for u in layers[0].units}


def test_selected_resolves_to_the_reporting_unit(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "All^Selected", unit_rows, {"u2"})
    assert {u.unit_id for u in layers[1].units} == {"u2"}


def test_selected_can_resolve_to_more_than_one_unit(numeric_series, unit_rows):
    """
    Documented: "'Selected' can legitimately resolve to more than one unit,
    and both are highlighted." Two submissions from one organisation.
    """
    layers = build_population_layers(numeric_series, "All^Selected", unit_rows, {"u1", "u2"})
    assert {u.unit_id for u in layers[1].units} == {"u1", "u2"}


def test_selected_with_nothing_selected_gives_an_empty_layer_not_everything(numeric_series, unit_rows):
    """
    The dangerous failure would be the opposite: falling back to the whole
    population and highlighting every unit as the reporting unit.
    """
    layers = build_population_layers(numeric_series, "All^Selected", unit_rows, set())
    assert layers[1].units == []


def test_a_reporting_unit_with_no_data_still_produces_its_selected_layer(numeric_series, unit_rows):
    """
    Stated explicitly in the docstring: "Whether the reporting unit has data
    for this chart must never be why a token disappears." u4 submitted
    nothing for this metric and must still get its layer.
    """
    layers = build_population_layers(numeric_series, "All^Selected", unit_rows, {"u4"})
    assert len(layers) == 2
    assert {u.unit_id for u in layers[1].units} == {"u4"}


# ---------------------------------------------------------------------------
# Peer groups
# ---------------------------------------------------------------------------

def test_a_named_peer_group_resolves_to_the_units_in_that_group(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "All^Region(North)", unit_rows, {"u1"})
    assert {u.unit_id for u in layers[1].units} == {"u1", "u2"}


def test_an_empty_bracket_peer_group_uses_the_reporting_unit_s_own_group(numeric_series, unit_rows):
    """
    "Region()" means "whichever region the reporting unit is in", resolved
    per unit at run time. u3 is in the South.
    """
    layers = build_population_layers(numeric_series, "All^Region()", unit_rows, {"u3"})
    assert {u.unit_id for u in layers[1].units} == {"u3"}
    assert layers[1].population_label == "South"


def test_a_reporting_unit_marked_as_no_group_gets_an_empty_peer_layer(numeric_series, unit_rows):
    """
    u4's Region() is "x", which means no group. It must not gather every
    other unit also marked "x" into a group called "x".
    """
    layers = build_population_layers(numeric_series, "All^Region()", unit_rows, {"u4"})
    assert len(layers) == 2
    assert layers[1].units == []


def test_a_named_peer_group_layer_is_labelled_with_the_group_name(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "Region(North)", unit_rows, {"u1"})
    assert layers[0].population_label == "North"


# ---------------------------------------------------------------------------
# The first token is the scope, and later tokens are subsets of it
# ---------------------------------------------------------------------------

def test_a_later_token_is_narrowed_to_the_scope(numeric_series, unit_rows):
    """
    With North as the scope, Selected only resolves if the reporting unit is
    itself in the North. u3 is in the South, so it falls outside the
    comparison being drawn.
    """
    layers = build_population_layers(numeric_series, "Region(North)^Selected", unit_rows, {"u3"})
    assert layers[1].units == []


def test_a_later_token_inside_the_scope_still_resolves(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "Region(North)^Selected", unit_rows, {"u1"})
    assert {u.unit_id for u in layers[1].units} == {"u1"}


def test_an_empty_scope_does_not_collapse_the_layer_list(numeric_series, unit_rows):
    """
    Documented: "The scope may resolve empty. Every later token then
    resolves empty against it, rather than the layer list collapsing."
    Three tokens still means three layers.
    """
    layers = build_population_layers(
        numeric_series, "Region(Atlantis)^Selected^Region(North)", unit_rows, {"u1"},
    )
    assert len(layers) == 3
    assert all(layer.units == [] for layer in layers)


# ---------------------------------------------------------------------------
# Each layer is a real, independently correct shape
# ---------------------------------------------------------------------------

def test_each_layer_has_its_own_recalculated_statistics(numeric_series, unit_rows):
    """
    The whole purpose of layering. The North mean must be the North mean,
    not the overall mean repeated.
    """
    layers = build_population_layers(numeric_series, "All^Region(North)", unit_rows, {"u1"})
    all_layer, north_layer = layers
    assert all_layer.metric_stats[0].mean == 20.0     # 10, 20, 30 and one blank
    assert north_layer.metric_stats[0].mean == 15.0   # 10 and 20


def test_building_layers_does_not_alter_the_shape_they_came_from(numeric_series, unit_rows):
    """
    Every layer filters the same original shape, so mutating it would make
    each layer after the first wrong.
    """
    before_units = [u.unit_id for u in numeric_series.units]
    before_mean = numeric_series.metric_stats[0].mean

    build_population_layers(numeric_series, "All^Selected^Region(North)", unit_rows, {"u1"})

    assert [u.unit_id for u in numeric_series.units] == before_units
    assert numeric_series.metric_stats[0].mean == before_mean
    assert numeric_series.population_label is None


def test_each_layer_keeps_the_descriptive_fields_of_the_original(numeric_series, unit_rows):
    layers = build_population_layers(numeric_series, "All^Selected", unit_rows, {"u1"})
    for layer in layers:
        assert layer.title == numeric_series.title
        assert layer.population_table == numeric_series.population_table
        assert layer.metric_names == numeric_series.metric_names


def test_the_only_thing_distinguishing_a_layer_is_its_population_label(numeric_series, unit_rows):
    """
    "A filtered copy is still a data shape, distinguished only by its
    population_label field."
    """
    layers = build_population_layers(numeric_series, "All^Selected", unit_rows, {"u1"})
    assert layers[0].population_label == "All"
    assert layers[1].population_label == "Selected"
