"""
formatting.py
Display-only formatting helpers. Nothing here touches report generation —
purely presentation for the Streamlit UI.
"""

import datetime


def _build_rows_html(rows):
    """Build the <tr> rows for the Outputs tab's run log table."""
    parts = []
    for r in rows:
        status_col  = "#2e7d32" if r["ok"] else "#c62828"
        status_icon = "✓" if r["ok"] else "✗"
        err_td = (
            f'<td style="padding:2px 8px;color:#c62828;font-size:0.9em;">{r["error"]}</td>'
            if r["error"] else "<td></td>"
        )
        parts.append(
            f'<tr style="font-size:0.82em;">'
            f'<td style="padding:2px 8px;color:#888;">{r["idx"]}</td>'
            f'<td style="padding:2px 8px;font-weight:600;">{r["code"]}</td>'
            f'<td style="padding:2px 8px;">{r["name"]}</td>'
            f'<td style="padding:2px 8px;color:{status_col};font-weight:700;">{status_icon}</td>'
            f'<td style="padding:2px 8px;color:#555;">{r["elapsed"]:.1f}s</td>'
            + err_td +
            "</tr>"
        )
    return "".join(parts)


def render_run_log_html(log_placeholder, rows_log):
    """Render the Outputs tab's live run log as a styled HTML table into log_placeholder."""
    bc        = "#e6f4ea" if all(r["ok"] for r in rows_log) else "#fff3e0"
    bc_border = "#4CAF50" if all(r["ok"] for r in rows_log) else "#E87722"
    log_placeholder.markdown(
        f"<div style='border-left:4px solid {bc_border};background:{bc};"
        f"border-radius:4px;padding:8px 14px;'>"
        f"<table style='width:100%;border-collapse:collapse;'>"
        f"<thead><tr style='font-size:0.78em;color:#666;border-bottom:1px solid #ccc;'>"
        f"<th style='padding:2px 8px;text-align:left;'>#</th>"
        f"<th style='padding:2px 8px;text-align:left;'>Code</th>"
        f"<th style='padding:2px 8px;text-align:left;'>Name</th>"
        f"<th style='padding:2px 8px;text-align:left;'>Status</th>"
        f"<th style='padding:2px 8px;text-align:left;'>Time</th>"
        f"<th style='padding:2px 8px;text-align:left;'>Error</th>"
        f"</tr></thead>"
        f"<tbody>{_build_rows_html(rows_log)}</tbody>"
        f"</table></div>",
        unsafe_allow_html=True,
    )


def format_uk_time(iso_str: str) -> str:
    """Convert a stored UTC ISO timestamp to UK local time (GMT/BST aware)."""
    if not iso_str:
        return ""
    try:
        from zoneinfo import ZoneInfo
        dt = datetime.datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        uk_dt = dt.astimezone(ZoneInfo("Europe/London"))
        return uk_dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso_str[:16].replace("T", " ")
