"""
gate.py
Custom Charts static validation and compilation.

Two separate steps, deliberately not merged:
  - validate_custom_chart_code: a static check over the code's structure
    (imports, banned names, function shape) — runs before anything is
    compiled or executed. This is the whole of the "AST gate" — no
    sandboxing, no runtime isolation (Decisions.md). It can confirm the
    function accepts the right inputs; it cannot confirm what the function
    returns, since Python doesn't enforce return types statically.
  - compile_custom_chart: turns already-validated source text into a
    callable. Whether the callable actually returns valid image bytes is
    only knowable by calling it — that check lives at the render call site,
    not here.

A Base Chart file may define any number of top-level functions — every
built-in already does (its own inlined palette/sizing/formatting helpers,
Decisions.md — no shared internal helpers module, each file is fully
standalone). Only one of those functions is the entry point the system
actually calls: whichever one carries the chart_inputs signature
(population_layers, width_emu, height_emu, tweaks). The other functions are
private helpers, exactly like every existing Base Chart already has, and
are not counted or restricted here beyond the shared import/banned-name
checks that apply to the whole file.
"""

import ast


class CustomChartError(Exception):
    """Raised when custom chart code fails validation or compilation."""
    pass


REQUIRED_PARAMS = ["population_layers", "width_emu", "height_emu", "tweaks"]


def _is_entry_point(func: ast.FunctionDef) -> bool:
    """A top-level function counts as the chart's entry point if its
    parameter names include every chart_inputs parameter — extra
    parameters or a different order aren't checked here, only presence."""
    param_names = [a.arg for a in func.args.args]
    return all(p in param_names for p in REQUIRED_PARAMS)


def validate_custom_chart_code(code_text: str) -> str:
    """
    Static validation only. Returns the name of the one entry-point
    function (the one matching the chart_inputs signature) on success.
    Raises CustomChartError with a plain-language reason on failure. Does
    not execute the code.
    """
    from core.output_generation.execution.charts.custom_charts.contract import (
        ALLOWED_IMPORTS, BANNED_NAMES,
    )

    if not code_text or not code_text.strip():
        raise CustomChartError("No code provided.")

    try:
        tree = ast.parse(code_text)
    except SyntaxError as e:
        raise CustomChartError(f"Code does not parse as valid Python: {e}")

    top_level_funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not top_level_funcs:
        raise CustomChartError(
            "No function definition found. A Base Chart needs at least one "
            f"function accepting {', '.join(REQUIRED_PARAMS)}."
        )

    entry_points = [f for f in top_level_funcs if _is_entry_point(f)]
    if len(entry_points) == 0:
        raise CustomChartError(
            "No function found matching the required entry-point signature: "
            f"def your_chart_name({', '.join(REQUIRED_PARAMS)}). "
            "Other helper functions are fine alongside it, but exactly one "
            "function must accept these four parameters."
        )
    if len(entry_points) > 1:
        names = ", ".join(f.name for f in entry_points)
        raise CustomChartError(
            f"Found {len(entry_points)} functions matching the entry-point signature "
            f"({names}) — exactly one is required. Rename or merge the others as "
            "helper functions with a different signature."
        )
    func = entry_points[0]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORTS:
                    raise CustomChartError(
                        f"Import of '{alias.name}' is not allowed. "
                        f"Allowed libraries: {', '.join(ALLOWED_IMPORTS)}."
                    )
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root not in ALLOWED_IMPORTS:
                raise CustomChartError(
                    f"Import from '{node.module}' is not allowed. "
                    f"Allowed libraries: {', '.join(ALLOWED_IMPORTS)}."
                )
        elif isinstance(node, ast.Name) and node.id in BANNED_NAMES:
            raise CustomChartError(f"Use of '{node.id}' is not allowed in a Base Chart function.")

    return func.name


def compile_custom_chart(code_text: str):
    """
    Compile already-validated source text into a callable. Executes the
    code in a fresh namespace and returns the entry-point function it
    defines — any other functions in the same file are compiled into the
    same namespace alongside it, so they resolve as ordinary module-level
    helpers, exactly as they would inside any of the built-in Base Chart
    files. Callers must run validate_custom_chart_code first — this
    function does not re-validate.
    """
    func_name = validate_custom_chart_code(code_text)
    namespace = {}
    exec(compile(code_text, "<custom_chart>", "exec"), namespace)
    return namespace[func_name]
