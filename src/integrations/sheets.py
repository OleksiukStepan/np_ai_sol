from __future__ import annotations

import logging
from pathlib import Path

import gspread
from gspread.utils import rowcol_to_a1

from src.models import ClassifiedRequest

logger = logging.getLogger(__name__)

_HEADER = [
    "id",
    "channel",
    "timestamp",
    "category",
    "target_department",
    "priority",
    "short_summary",
    "requested_actions",
    "needs_clarification",
    "confidence",
    "urgency_signals",
    "is_actionable",
    "estimated_effort",
    "classification_error",
]


def _row(item: ClassifiedRequest) -> list[str]:
    return [
        item.id,
        item.channel,
        item.timestamp,
        item.category.value,
        item.target_department or "",
        item.priority.value,
        item.short_summary,
        "\n".join(item.requested_actions),
        str(item.needs_clarification),
        f"{item.confidence:.2f}",
        " | ".join(item.urgency_signals),
        str(item.is_actionable),
        item.estimated_effort.value,
        item.classification_error or "",
    ]


def _column_letter(num_cols: int) -> str:
    a1 = rowcol_to_a1(1, num_cols)  # e.g. (1, 14) -> "N1"
    return "".join(char for char in a1 if char.isalpha())


def _style_block(worksheet, start_row: int, num_cols: int) -> None:
    """Style the date separator (merged, centered, bold) and the header row."""
    last_col = _column_letter(num_cols)
    date_range = f"A{start_row}:{last_col}{start_row}"
    worksheet.merge_cells(date_range)
    worksheet.format(
        date_range,
        {
            "horizontalAlignment": "CENTER",
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.85, "green": 0.9, "blue": 1.0},
        },
    )
    header_row = start_row + 1
    worksheet.format(
        f"A{header_row}:{last_col}{header_row}",
        {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.92, "green": 0.92, "blue": 0.92},
        },
    )


def export(
    sheet_id: str,
    service_account_json: str,
    results: list[ClassifiedRequest],
    run_date: str,
) -> bool:
    """Append a dated block (date separator + header + rows). Never overwrites."""
    if not Path(service_account_json).exists():
        logger.error("Service account file not found: %s", service_account_json)
        return False
    try:
        client = gspread.service_account(filename=service_account_json)
        worksheet = client.open_by_key(sheet_id).sheet1
        existing = worksheet.get_all_values()
        start_row = len(existing) + 2 if existing else 1  # blank gap between runs
        block = [[f"Запити за {run_date}"], _HEADER]
        block += [_row(item) for item in results]
        worksheet.update(values=block, range_name=f"A{start_row}")
        _style_block(worksheet, start_row, len(_HEADER))
        return True
    except Exception as err:  # gspread/auth errors
        logger.error("Google Sheets export failed: %s", err)
        return False
