"""
results.py
Shared result-dict shape returned by every Running Order function (create_ppt,
insert_chart, insert_picture, insert_from_excel, save_ppt, etc). Kept local to
output_generation/execution — only consumed within this concern, not global.
"""


def ok_result(row: dict, message: str) -> dict:
    """Build a success result dict for a Running Order row."""
    return {
        "status": "ok",
        "row_id": row.get("row_id", ""),
        "function": row.get("function", ""),
        "message": message,
    }


def err_result(row: dict, message: str) -> dict:
    """Build an error result dict for a Running Order row."""
    return {
        "status": "error",
        "row_id": row.get("row_id", ""),
        "function": row.get("function", ""),
        "message": message,
    }
