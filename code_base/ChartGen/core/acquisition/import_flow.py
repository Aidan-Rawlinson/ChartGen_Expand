"""
import_flow.py
Coordinator for the "process template" sequence: read the uploaded template,
merge any extracted toolkit URLs into WorkfileState's manifest table, then
generate the Running Order from the result. Sequencing only — no logic of
its own; each step is delegated to the concern that owns it.

Data fetching is deliberately not part of this sequence — template
processing populates the manifest table only, and the single fetch process
(the Imports tab's Fetch button, core.acquisition.fetch_dispatch) is the
one place data is pulled.

Also the target for the second trigger described in Architecture Decision 2
(Running Order regeneration after a structural template re-upload) — this is
why this coordinator lives here rather than as a one-off function inside the
Imports tab: the capability isn't unique to that tab.

output_generation.definition.running_order never imports this module or
anything under acquisition — only this coordinator knows about both
concerns, so there is no two-way dependency between them.
"""

from core.acquisition.template.template_reader import read_template
from core.acquisition.url_triage import url_to_database
from core.workfile.state.workfile_file import new_manifest_row, renumber_chart_refs
from core.output_generation.execution.charts.cache_reader import load_manifest
from core.output_generation.definition.running_order import (
    generate_from_template, backfill_default_chart_types,
)


def merge_urls_into_manifest(urls: list[str], source: str, *, workfile_state) -> dict:
    """
    Merge a list of URLs into the manifest table. Existing live rows are
    left untouched; a URL matching only a deleted row resurrects that row
    (deleted=0, same hex_id, cached data intact); genuinely new URLs get a
    new row with a fresh hex_id. chart_refs are renumbered afterwards.

    Returns {"added": int, "resurrected": int, "already_present": int}.
    """
    by_url = {}
    for row in workfile_state.manifest_rows:
        by_url.setdefault(row.get("url", "").strip(), row)

    added = resurrected = already_present = 0
    for url in urls:
        url = url.strip()
        if not url:
            continue
        existing = by_url.get(url)
        if existing is None:
            row = new_manifest_row(url, source, workfile_state.manifest_rows, url_to_database(url))
            workfile_state.manifest_rows.append(row)
            by_url[url] = row
            added += 1
        elif str(existing.get("deleted", "0")) == "1":
            existing["deleted"] = "0"
            resurrected += 1
        else:
            already_present += 1

    if added or resurrected:
        renumber_chart_refs(workfile_state.manifest_rows)
        workfile_state.dirty = True

    return {"added": added, "resurrected": resurrected,
            "already_present": already_present}


def process_template(tmp_pptx_path: str, cleaned_output_path: str, *,
                      workfile_state) -> dict:
    """
    Run the template -> manifest merge -> Running Order sequence.

    1. Read the template (placeholders, yellow-box classification, cleaned copy).
    2. Save the cleaned copy to cleaned_output_path and store its bytes on
       workfile_state.
    3. Merge any extracted toolkit URLs into the manifest table (new rows
       added, existing preserved, deleted rows resurrected). No fetch.
    4. Generate the Running Order from the template read result and the
       manifest table — chart rows get cache_file={hex_id}.json immediately;
       chart_type_ref stays blank until Fetch backfills it (see
       backfill_chart_types_after_fetch, below).

    Returns:
    {
        "template_result": TemplateReadResult,
        "new_urls_added": int,
        "urls_resurrected": int,
        "new_urls_already_present": int,
        "running_order_rows": list[dict],
    }
    """
    template_result = read_template(tmp_pptx_path)

    with open(cleaned_output_path, "wb") as f:
        f.write(template_result.cleaned_pptx_bytes)
    workfile_state.template_pptx_bytes = template_result.cleaned_pptx_bytes

    # Page size is workfile-level metadata, not a chart-specific fact — captured
    # once here, alongside the cleaned-template asset, for the Charts sheet's
    # percent-of-page-size sizing control (core.shared.infrastructure.page_sizing).
    workfile_state.settings["template_page_width_emu"] = str(template_result.slide_width)
    workfile_state.settings["template_page_height_emu"] = str(template_result.slide_height)

    urls = [p.url for p in template_result.placeholders if p.url]
    merge = merge_urls_into_manifest(urls, "Template", workfile_state=workfile_state)

    manifest = load_manifest(workfile_state)
    rows = generate_from_template(template_result, manifest)
    workfile_state.running_order_rows = rows
    workfile_state.dirty = True

    return {
        "template_result": template_result,
        "new_urls_added": merge["added"],
        "urls_resurrected": merge["resurrected"],
        "new_urls_already_present": merge["already_present"],
        "running_order_rows": rows,
    }


def backfill_chart_types_after_fetch(*, workfile_state) -> int:
    """
    Fill in chart_type_ref for any insert_chart Running Order row still
    blank, now that Fetch has resolved each chart's shape_type. Called once,
    at the end of the Fetch action (Imports tab) — this is the earliest
    point shape_type is known; Running Order generation always runs before
    Fetch, so generation time can never resolve this itself.

    Silent by design — no user-facing message. Never overwrites a
    chart_type_ref that's already set, whether from a prior backfill or a
    manual edit made between Process Template and Fetch.

    Returns the number of rows backfilled.
    """
    manifest = load_manifest(workfile_state)
    backfilled = backfill_default_chart_types(workfile_state.running_order_rows, manifest)
    if backfilled:
        workfile_state.dirty = True
    return backfilled
