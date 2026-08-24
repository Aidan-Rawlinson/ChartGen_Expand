# tests

Run them:

```
run_tests.bat
```

Roughly 340 checks, a few seconds. `pytest`, from `requirements-dev.txt`, which is deliberately separate from `requirements.txt`: that one builds every colleague's application venv and ships in the installer, and pytest has no business in either.

## The rule for what is tested

**ChartGen's own docstrings state its invariants, and those statements are the tests.**

Not every function. A test earns its place when it protects a promise the code makes that a later change could break silently, with a wrong report as the only symptom. Those promises are already written down, usually in the absolute sentences scattered through the docstrings and the `CLAUDE.md` files:

- `population_layers.py`: "Every non-blank token produces exactly one layer, in order, and is never dropped."
- `grid_store.resize_grid`: "growing the grid never silently rewrites sizes already authored elsewhere on it"
- `numeric_series._recalc_numeric_series_stats`: "Always returns exactly n_metrics entries, even when units is empty"
- `version_compatibility.is_file_version_compatible`: an absent version "is treated as incompatible, not assumed safe"
- root `CLAUDE.md`: "Stored values are never rewritten."

The corollary is that `to_base36(5) == "5"` needs no test. Nothing depends on it in a way anyone could accidentally break.

Test the promises, not the plumbing. A test that pins down *how* something works rather than *what it guarantees* will break on every legitimate change and earn nothing. If a test is ever in the way of a change that is genuinely correct, it was the wrong test: delete it. Tests here are not sacred.

Each test's name states the behaviour in plain English, and its docstring says which promise it protects and what would go wrong without it. That is so the choice of what to test can be reviewed against the intent it came from, rather than taken on trust.

## Layout

`tests/` mirrors `chartgen/`, one test file per code module, `test_` on the front. So "where does this test live" is never a judgement call, and a gap in the tree is a coverage map anyone can read.

`round_trips/` is the exception: those tests belong to no single module. The `.cgw` round trip and the six Excel pairs live there.

`--import-mode=importlib` in `pytest.ini` is required, not a preference. Seventeen module basenames are duplicated across `chartgen/`, so the mirrored test filenames are duplicated too, and pytest's default import mode cannot tell two same-named test modules apart.

## What is covered

| Area | What is pinned |
|---|---|
| `shared/infrastructure` | Period id extraction and rebuilding as exact inverses. Percent/EMU conversion, including the values the UI must not tidy up. Base-36 id issuing and the never-reissued rule. `soft_parents` parsing and one-hop resolution. The file-version gate. CSV type coercion |
| Running Order rows | `row_id` renumbering, insert placement, that Overwrite leaves other columns alone, where a new content row lands |
| Output Table grids | Grid geometry and the size row/column offsets, `validate_grid` staying advisory, `resize_grid` preserving authored sizes |
| The numeric core | The percentile convention written out longhand, that `None` is never averaged as zero, per-layer stats recalculation, `reference_ids`, the TimeSeries to NumericSeries conversion, `prepare_chart_cut` |
| Population layers | Every stated guarantee about tokens, scope and empty layers |
| Round trips | The `.cgw` format with every payload field populated. All six Excel export/import pairs |

## What is not covered, deliberately

- **The Streamlit UI.** Needs a browser harness, and would break on every layout change.
- **PowerPoint and Excel COM.** Needs Office installed, is slow, is environment-dependent.
- **Whether a chart looks right.** Pixel comparison of matplotlib output breaks on every matplotlib version bump.
- **The toolkit APIs.** No network calls from tests.

That is a large share of the application. It is why the suite stays small, and why a green run is not evidence the app is working. **A green run means logic that used to be right still is. It says nothing about how anything looks.** Only running ChartGen shows that.

## Conventions

All test data is invented. No real submission data, no real organisation names, no real workfile anywhere under `tests/`.

Anything that writes a file uses pytest's `tmp_path`. Nothing here touches a real workfile, `CG_Extracts`, or `.streamlit`.

Shared fixtures live in `conftest.py` and pytest supplies them by name; no test imports it. Fixtures that need to build several variants are factories (`make_numeric_series`, `make_time_series`) rather than ready-made objects.

Fixture rows are built from the real `FIELDNAMES` lists, not a hand-picked subset. A column outside the schema raises on save, and a column left out reads back as an empty string, so a hand-written subset would compare unequal for reasons that have nothing to do with the code.

Where a test records behaviour rather than endorsing it, the docstring says so.

## Proving the tests can fail

A test that can never fail is worse than no test: it manufactures confidence. Passing is not evidence on its own.

When this suite was built, four invariants were deliberately broken in the application code, one at a time, to confirm the tests caught each one and then reverted:

| Break | Caught by |
|---|---|
| Drop a population token that resolves to nobody | 6 tests |
| Let `resize_grid` redistribute authored column widths | 1 test |
| Swap linear interpolation for nearest-rank percentiles | 4 tests, reporting a median of 3.0 where 2.5 was expected |
| Stop writing `chart_store.csv` on save | the whole-format `.cgw` round trip |

Worth repeating on anything substantial added here. It is the only way to know a new test has teeth.
