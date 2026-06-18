from __future__ import annotations

import logging
from html import escape

import httpx

logger = logging.getLogger(__name__)

_CATEGORY_EMOJI = {
    "автоматизація": "⚙️",
    "інтеграція": "🔌",
    "звіт/аналітика": "📊",
    "баг/підтримка": "🐞",
    "питання/консультація": "❓",
    "поза скоупом": "🚫",
}
_PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
_PRIORITY_ORDER = ["high", "medium", "low"]
_TOP_DEPARTMENTS = 5


def _category_lines(by_category: dict) -> list[str]:
    ranked = sorted(by_category.items(), key=lambda item: -item[1])
    return [
        f"{_CATEGORY_EMOJI.get(name, '•')} {escape(name)} — <b>{count}</b>"
        for name, count in ranked
    ]


def _priority_lines(by_priority: dict) -> list[str]:
    lines = []
    for level in _PRIORITY_ORDER:
        if level in by_priority:
            lines.append(f"{_PRIORITY_EMOJI[level]} {level} — <b>{by_priority[level]}</b>")
    return lines


def _department_lines(by_department: dict) -> list[str]:
    named = {dept: count for dept, count in by_department.items() if dept != "—"}
    ranked = sorted(named.items(), key=lambda item: -item[1])[:_TOP_DEPARTMENTS]
    return [f"• {escape(dept)} — <b>{count}</b>" for dept, count in ranked]


def build_digest(summary: dict, run_date: str) -> str:
    """Render a structured, emoji-formatted HTML digest from the summary."""
    header = (
        f"📥 <b>Netpeak — дайджест запитів</b>\n"
        f"📅 {run_date}\n"
        f"Усього запитів: <b>{summary['total']}</b>"
    )
    blocks = [header]

    blocks.append("<b>За категорією</b>\n" + "\n".join(_category_lines(summary["by_category"])))
    blocks.append("<b>За пріоритетом</b>\n" + "\n".join(_priority_lines(summary["by_priority"])))

    departments = _department_lines(summary["by_department"])
    if departments:
        blocks.append("<b>Топ відділів</b>\n" + "\n".join(departments))

    footer = [f"⚠️ Потребують уточнення: <b>{len(summary['needs_clarification'])}</b>"]
    if summary["fallbacks"]:
        footer.append(f"❗ Не вдалося класифікувати: <b>{len(summary['fallbacks'])}</b>")
    blocks.append("\n".join(footer))

    return "\n\n".join(blocks)


def send_digest(bot_token: str, chat_id: str, summary: dict, run_date: str) -> bool:
    """Post the digest. Returns False on any failure (never raises)."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": build_digest(summary, run_date),
        "parse_mode": "HTML",
    }
    try:
        response = httpx.post(url, json=payload, timeout=15)
        response.raise_for_status()
        return True
    except httpx.HTTPError as err:
        logger.error("Telegram digest failed: %s", err)
        return False
