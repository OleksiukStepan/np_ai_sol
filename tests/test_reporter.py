from src.models import Category, ClassifiedRequest, InboxRequest, Priority
from src.reporter import build_summary, detect_duplicates


def _record(req_id, category, priority, summary, clarify=False):
    return ClassifiedRequest(
        id=req_id,
        channel="Slack",
        timestamp="t",
        raw_text="x",
        category=category,
        target_department="маркетинг",
        priority=priority,
        short_summary=summary,
        requested_actions=[],
        needs_clarification=clarify,
        confidence=0.9,
        urgency_signals=[],
        is_actionable=True,
        estimated_effort="low",
    )


def test_build_summary_counts():
    records = [
        _record("R1", Category.AUTOMATION, Priority.HIGH, "звіт Google Ads щотижня"),
        _record("R2", Category.AUTOMATION, Priority.LOW, "звіт Google Ads потрібен", True),
        _record("R3", Category.BUG_SUPPORT, Priority.MEDIUM, "інше зовсім питання"),
    ]
    summary = build_summary(records)
    assert summary["total"] == 3
    assert summary["by_category"]["автоматизація"] == 2
    assert summary["needs_clarification"] == ["R2"]


def test_detect_duplicates_finds_similar_summaries():
    records = [
        _record("R1", Category.REPORT_ANALYTICS, Priority.HIGH, "щотижневий звіт google ads метрики"),
        _record("R2", Category.REPORT_ANALYTICS, Priority.MEDIUM, "щотижневий звіт google ads метрики"),
        _record("R3", Category.BUG_SUPPORT, Priority.LOW, "зовсім інша тема підтримки"),
    ]
    duplicates = detect_duplicates(records)
    assert ("R1", "R2", 1.0) in duplicates


def test_fallback_records_not_flagged_as_duplicates():
    base = InboxRequest(id="R1", channel="Slack", timestamp="t", raw_text="x")
    fallbacks = [
        ClassifiedRequest.fallback(base.model_copy(update={"id": "F1"}), "err"),
        ClassifiedRequest.fallback(base.model_copy(update={"id": "F2"}), "err"),
    ]
    assert detect_duplicates(fallbacks) == []
