"""
xlsx_writer.py
Writes Running Order rows to a formatted .xlsx file, with dropdown
validation on function, chart_type_ref, and enabled, and colour-coding by
row type.
"""

from core.output_generation.definition.running_order.schema import (
    COLUMNS, ALL_FUNCTIONS, SCOPE_VALUES, STRUCTURAL_FUNCTIONS,
)
from core.output_generation.definition.running_order.dialog_support import (
    get_valid_chart_refs_for_cache_file,
)

try:
    import openpyxl
    from openpyxl.styles import (
        PatternFill, Font, Alignment, Border, Side
    )
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


def write_xlsx(rows: list[dict], output_path: str,
               manifest: dict = None):
    """Write Running Order rows to a formatted .xlsx file with dropdown validation on function, chart_type_ref, and enabled."""
    if not OPENPYXL_AVAILABLE:
        raise ImportError("openpyxl is required to write the Running Order xlsx.")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Running Order"

    # --- Styles ---
    NAVY = "071A34"
    CRIMSON = "C12958"
    LIGHT_GREY = "F2F2F2"
    MID_GREY = "D9D9D9"
    WHITE = "FFFFFF"
    DISABLED_GREY = "AAAAAA"
    CHART_GREEN = "E8F5E9"
    PICTURE_TEAL = "E0F7FA"
    EXCEL_PURPLE = "F3E5F5"
    BATCH_ORANGE = "FFF3E0"
    STRUCTURAL_BLUE = "E3F2FD"
    POPULATIONS_AMBER = "FFF8E1"

    header_fill = PatternFill("solid", fgColor=NAVY)
    header_font = Font(color=WHITE, bold=True, size=10)
    structural_fill = PatternFill("solid", fgColor=STRUCTURAL_BLUE)
    chart_fill = PatternFill("solid", fgColor=CHART_GREEN)
    disabled_font = Font(color=DISABLED_GREY, size=10)
    normal_font = Font(size=10)
    centre_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin = Side(style="thin", color=MID_GREY)
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # --- Column widths ---
    col_widths = {
        "row_id":        6,
        "enabled":       8,
        "scope":         13,
        "function":      22,
        "slide_index":   11,
        "placeholder":   18,
        "chart_type_ref":22,
        "cache_file":    30,
        "populations":   30,
        "image_path":    36,
        "excel_path":    36,
        "export_range":  18,
        "driver_range":  18,
        "left_emu":      12,
        "top_emu":       12,
        "width_emu":     12,
        "height_emu":    12,
        "notes":         40,
    }

    # --- Header row ---
    for col_idx, col_name in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = centre_align
        cell.border = border
        ws.column_dimensions[get_column_letter(col_idx)].width = col_widths.get(col_name, 14)

    ws.row_dimensions[1].height = 20
    ws.freeze_panes = "A2"

    # --- Data validation: function dropdown (applies to entire function column) ---
    func_dv = DataValidation(
        type="list",
        formula1='"' + ",".join(ALL_FUNCTIONS) + '"',
        allow_blank=False,
        showDropDown=False,
    )
    ws.add_data_validation(func_dv)

    enabled_dv = DataValidation(
        type="list",
        formula1='"1,0"',
        allow_blank=False,
        showDropDown=False,
    )
    ws.add_data_validation(enabled_dv)

    scope_dv = DataValidation(
        type="list",
        formula1='"' + ",".join(SCOPE_VALUES) + '"',
        allow_blank=False,
        showDropDown=False,
    )
    ws.add_data_validation(scope_dv)

    # --- Data rows ---
    for data_row_idx, row in enumerate(rows, start=2):
        excel_row = data_row_idx
        is_enabled = str(row.get("enabled", "1")) == "1"
        func  = row.get("function", "")
        scope = str(row.get("scope", "normal")).strip()
        is_structural = func in STRUCTURAL_FUNCTIONS

        for col_idx, col_name in enumerate(COLUMNS, start=1):
            value = row.get(col_name, "")
            if value == "" or value is None:
                value = ""
            cell = ws.cell(row=excel_row, column=col_idx, value=value)
            cell.border = border
            cell.font = disabled_font if not is_enabled else normal_font

            if scope in ("batch_open", "batch_close"):
                cell.fill = PatternFill("solid", fgColor=BATCH_ORANGE)
            elif is_structural and func == "set_default_populations":
                cell.fill = PatternFill("solid", fgColor=POPULATIONS_AMBER)
            elif is_structural:
                cell.fill = structural_fill
            elif func == "insert_chart":
                cell.fill = chart_fill
            elif func == "insert_picture":
                cell.fill = PatternFill("solid", fgColor=PICTURE_TEAL)
            elif func in ("insert_from_excel",):
                cell.fill = PatternFill("solid", fgColor=EXCEL_PURPLE)
            else:
                cell.fill = PatternFill("solid", fgColor=LIGHT_GREY)

            # Alignment
            if col_name in ("row_id", "enabled", "slide_index",
                            "left_emu", "top_emu", "width_emu", "height_emu"):
                cell.alignment = centre_align
            else:
                cell.alignment = left_align

        # Apply function dropdown
        func_col = COLUMNS.index("function") + 1
        func_dv.add(ws.cell(row=excel_row, column=func_col))

        # Apply enabled dropdown
        enabled_col = COLUMNS.index("enabled") + 1
        enabled_dv.add(ws.cell(row=excel_row, column=enabled_col))

        # Apply scope dropdown
        scope_col = COLUMNS.index("scope") + 1
        scope_dv.add(ws.cell(row=excel_row, column=scope_col))

        # Per-row chart_type_ref dropdown — constrained to the valid chart
        # refs for the row's data shape via the shared rule in dialog_support
        # (which itself falls back to all refs if the shape is unknown).
        if func == "insert_chart":
            cache_file = str(row.get("cache_file") or "").strip()
            if cache_file.lower() == "none":
                cache_file = ""
            chart_refs = get_valid_chart_refs_for_cache_file(cache_file, manifest or {})

            if chart_refs:
                ref_formula = '"' + ",".join(chart_refs) + '"'
                chart_dv = DataValidation(
                    type="list",
                    formula1=ref_formula,
                    allow_blank=True,
                    showDropDown=False,
                )
                ws.add_data_validation(chart_dv)
                ctr_col = COLUMNS.index("chart_type_ref") + 1
                chart_dv.add(ws.cell(row=excel_row, column=ctr_col))

        ws.row_dimensions[excel_row].height = 18

    wb.save(output_path)
    return output_path
