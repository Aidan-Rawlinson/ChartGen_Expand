"""
import_flow.py
Coordinator for the "process template" sequence: read the uploaded template,
merge any extracted toolkit URLs into WorkfileState.urls, fetch all chart
data, then generate the Running Order from the result. Sequencing only — no
logic of its own; each step is delegated to the concern that owns it.

Also the target for the second trigger described in Architecture Decision 2
(Running Order regeneration after a structural template re-upload) — this is
why this coordinator lives here rather than as a one-off function inside the
Imports tab: the capability isn't unique to that tab.

output_generation.definition.running_order never imports this module or
anything under acquisition — only this coordinator knows about both
concerns, so there is no two-way dependency between them.
"""

from core.acquisition.template.template_reader import read_template
from core.acquisition.toolkit_nhs.fetch import fetch_all
from core.output_generation.execution.charts.cache_reader import load_manifest
from core.output_generation.definition.running_order import generate_from_template


def process_template(tmp_pptx_path: str, cleaned_output_path: str, *,
                      workfile_state, token: str, on_fetch_progress=None) -> dict:
    """
    Run the full template -> fetch -> Running Order sequence.

    1. Read the template (placeholders, yellow-box classification, cleaned copy).
    2. Save the cleaned copy to cleaned_output_path and store its bytes on
       workfile_state.
    3. Merge any extracted toolkit URLs into workfile_state.urls (new ones
       added, existing ones preserved).
    4. Fetch all chart data (full refresh) if any URLs were found.
    5. Generate the Running Order from the template read result and the
       resulting cache manifest.

    Returns:
    {
        "template_result": TemplateReadResult,
        "new_urls_added": int,
        "new_urls_already_present": int,
        "fetch_results": list[dict],
        "running_order_rows": list[dict],
    }
    """
    template_result = read_template(tmp_pptx_path)

    with open(cleaned_output_path, "wb") as f:
        f.write(template_result.cleaned_pptx_bytes)
    workfile_state.template_pptx_bytes = template_result.cleaned_pptx_bytes

    new_urls = [{"url": p.url, "label": p.label} for p in template_result.placeholders if p.url]
    existing = {u["url"] for u in workfile_state.urls}
    added = 0
    for u in new_urls:
        if u["url"] not in existing:
            workfile_state.urls.append(u)
            added += 1
    already_present = len(new_urls) - added

    fetch_results = []
    if new_urls:
        fetch_results = fetch_all(token, on_progress=on_fetch_progress, workfile_state=workfile_state)

    manifest = load_manifest(workfile_state)
    rows = generate_from_template(template_result, manifest)
    workfile_state.running_order_rows = rows
    workfile_state.dirty = True

    return {
        "template_result": template_result,
        "new_urls_added": added,
        "new_urls_already_present": already_present,
        "fetch_results": fetch_results,
        "running_order_rows": rows,
    }
