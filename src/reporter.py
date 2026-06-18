from __future__ import annotations

import json
import re
from collections import Counter
from itertools import combinations
from pathlib import Path

from src.models import ClassifiedRequest

_WORD_RE = re.compile(r"\w{4,}", re.UNICODE)
_DUP_THRESHOLD = 0.5


def _keywords(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def detect_duplicates(
    results: list[ClassifiedRequest],
) -> list[tuple[str, str, float]]:
    """Best-effort: same category + high keyword overlap of summaries."""
    pairs: list[tuple[str, str, float]] = []
    classified = [item for item in results if not item.classification_error]
    for left, right in combinations(classified, 2):
        if left.category is not right.category:
            continue
        words_left = _keywords(left.short_summary)
        words_right = _keywords(right.short_summary)
        if not words_left or not words_right:
            continue
        overlap = len(words_left & words_right) / len(words_left | words_right)
        if overlap >= _DUP_THRESHOLD:
            pairs.append((left.id, right.id, round(overlap, 2)))
    return pairs


def build_summary(results: list[ClassifiedRequest]) -> dict:
    """Compute aggregates used by both report.md and output.json meta."""
    return {
        "total": len(results),
        "by_category": dict(
            Counter(record.category.value for record in results)
        ),
        "by_priority": dict(
            Counter(record.priority.value for record in results)
        ),
        "by_effort": dict(
            Counter(record.estimated_effort.value for record in results)
        ),
        "by_department": dict(
            Counter(record.target_department or "—" for record in results)
        ),
        "needs_clarification": [
            record.id for record in results if record.needs_clarification
        ],
        "fallbacks": [
            record.id for record in results if record.classification_error
        ],
        "possible_duplicates": detect_duplicates(results),
    }


def _render_counts(title: str, counts: dict) -> list[str]:
    lines = [f"## {title}", ""]
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    for key, count in ordered:
        lines.append(f"- {key}: {count}")
    lines.append("")
    return lines


def render_report(results: list[ClassifiedRequest], summary: dict) -> str:
    by_id = {record.id: record for record in results}
    lines = ["# Зведений звіт по запитах", ""]
    lines.append(f"Усього запитів: **{summary['total']}**")
    lines.append("")
    lines += _render_counts("За категорією", summary["by_category"])
    lines += _render_counts("За пріоритетом", summary["by_priority"])
    lines += _render_counts("За трудовитратами", summary["by_effort"])
    lines += _render_counts("За відділом", summary["by_department"])

    lines += ["## Потребують уточнення", ""]
    if summary["needs_clarification"]:
        for req_id in summary["needs_clarification"]:
            lines.append(f"- {req_id}: {by_id[req_id].short_summary}")
    else:
        lines.append("- немає")
    lines.append("")

    if summary["possible_duplicates"]:
        lines += ["## Можливі дублікати (евристика)", ""]
        for left, right, score in summary["possible_duplicates"]:
            lines.append(f"- {left} ↔ {right} (схожість {score})")
        lines.append("")

    if summary["fallbacks"]:
        lines += ["## Не вдалося класифікувати (fallback)", ""]
        for req_id in summary["fallbacks"]:
            lines.append(f"- {req_id}")
        lines.append("")

    return "\n".join(lines)


def write_outputs(
    results: list[ClassifiedRequest], output_dir: str | Path, meta: dict
) -> dict:
    """Write output.json and report.md; return the computed summary."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    summary = build_summary(results)

    payload = {
        "meta": {**meta, "summary": summary},
        "requests": [record.model_dump(mode="json") for record in results],
    }
    (out_path / "output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_path / "report.md").write_text(
        render_report(results, summary), encoding="utf-8"
    )
    return summary
