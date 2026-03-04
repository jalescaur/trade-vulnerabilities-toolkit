"""
src/io/excel_format.py
======================
"Official" Excel formatting for chapter-ready tables.

Goals:
- Consistent style across all output tables
- Readable in print (grayscale)
- Minimal but professional: title row, bold header, thin borders, freeze panes
- Sensible number formats:
  - values: thousands separators
  - shares/ratios: percent
  - rates: percent with 1-2 decimals

Implementation:
- Uses openpyxl via pandas ExcelWriter.
- Avoids heavy styling so it's robust across Excel/LibreOffice.

NOTE:
- If you have a specific "official print" template, we can match it exactly.
  For now, we implement a clean standard suitable for publication appendices.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows


@dataclass(frozen=True)
class ExcelStyle:
    title_font: Font = Font(name="Calibri", size=14, bold=True)
    header_font: Font = Font(name="Calibri", size=11, bold=True)
    body_font: Font = Font(name="Calibri", size=11, bold=False)

    title_alignment: Alignment = Alignment(horizontal="left", vertical="center")
    header_alignment: Alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    body_alignment: Alignment = Alignment(horizontal="left", vertical="top", wrap_text=False)

    header_fill: PatternFill = PatternFill("solid", fgColor="E6E6E6")  # light gray
    thin_border: Border = Border(
        left=Side(style="thin", color="A0A0A0"),
        right=Side(style="thin", color="A0A0A0"),
        top=Side(style="thin", color="A0A0A0"),
        bottom=Side(style="thin", color="A0A0A0"),
    )


DEFAULT_STYLE = ExcelStyle()


def _auto_fit_columns(ws, min_width: int = 10, max_width: int = 55) -> None:
    """Auto-fit column widths based on cell string lengths (best-effort)."""
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value is None:
                continue
            s = str(cell.value)
            max_len = max(max_len, len(s))
        ws.column_dimensions[col_letter].width = max(min_width, min(max_width, max_len + 2))


def write_excel_table(
    df: pd.DataFrame,
    path: Path,
    sheet_name: str,
    title: str,
    note: str | None = None,
    percent_cols: Iterable[str] = (),
    int_cols: Iterable[str] = (),
    float_cols: Iterable[str] = (),
    currency_cols: Iterable[str] = (),
    freeze_at: str = "A3",
    style: ExcelStyle = DEFAULT_STYLE,
) -> Path:
    """
    Create a single-sheet Excel workbook with consistent "official" formatting.

    Row layout:
    - Row 1: Title (merged across columns)
    - Row 2: Header
    - Row 3+: Data
    - Optional final row(s): note

    Number formats:
    - percent_cols -> 0.0%
    - int_cols -> #,##0
    - float_cols -> #,##0.00
    - currency_cols -> #,##0 (generic; adjust if you want USD symbol)
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]  # Excel limit

    ncols = max(1, df.shape[1])

    # Title row
    ws.cell(row=1, column=1, value=title)
    ws.cell(row=1, column=1).font = style.title_font
    ws.cell(row=1, column=1).alignment = style.title_alignment
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)

    # Header + data via dataframe_to_rows
    for r_idx, row in enumerate(dataframe_to_rows(df, index=False, header=True), start=2):
        ws.append(row)
        if r_idx == 2:
            # Header styling
            for c_idx in range(1, ncols + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.font = style.header_font
                cell.fill = style.header_fill
                cell.alignment = style.header_alignment
                cell.border = style.thin_border
        else:
            # Body styling
            for c_idx in range(1, ncols + 1):
                cell = ws.cell(row=r_idx, column=c_idx)
                cell.font = style.body_font
                cell.alignment = style.body_alignment
                cell.border = style.thin_border

    # Freeze panes (keeps title+header visible)
    ws.freeze_panes = freeze_at

    # Apply number formats by column name
    col_index = {name: i + 1 for i, name in enumerate(df.columns)}

    def _apply_fmt(cols: Iterable[str], fmt: str):
        for col in cols:
            if col not in col_index:
                continue
            j = col_index[col]
            for i in range(3, 3 + len(df)):
                ws.cell(row=i, column=j).number_format = fmt

    _apply_fmt(percent_cols, "0.0%")
    _apply_fmt(int_cols, "#,##0")
    _apply_fmt(float_cols, "#,##0.00")
    _apply_fmt(currency_cols, "#,##0")

    # Optional note
    if note:
        start = 3 + len(df) + 1
        ws.cell(row=start, column=1, value="Note:")
        ws.cell(row=start, column=1).font = Font(name="Calibri", size=10, bold=True)
        ws.cell(row=start, column=2, value=note)
        ws.cell(row=start, column=2).font = Font(name="Calibri", size=10)
        ws.merge_cells(start_row=start, start_column=2, end_row=start, end_column=ncols)

    _auto_fit_columns(ws)

    wb.save(path)
    return path