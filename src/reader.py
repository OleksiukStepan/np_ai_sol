from __future__ import annotations

import csv
from pathlib import Path

from src.models import InboxRequest

REQUIRED_COLUMNS = {"id", "channel", "timestamp", "raw_text"}


def read_requests(path: str | Path) -> list[InboxRequest]:
    """Parse the inbox CSV. Multi-line raw_text is handled by the csv module."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Input file not found: {csv_path}")

    with csv_path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {sorted(missing)}")

        requests: list[InboxRequest] = []
        for row in reader:
            if not (row.get("raw_text") or "").strip():
                continue
            requests.append(
                InboxRequest(
                    id=row["id"].strip(),
                    channel=row["channel"].strip(),
                    timestamp=row["timestamp"].strip(),
                    raw_text=row["raw_text"].strip(),
                )
            )
    return requests
