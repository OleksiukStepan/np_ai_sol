from src.models import Category, ClassifiedRequest, Classification, InboxRequest


def _request() -> InboxRequest:
    return InboxRequest(
        id="REQ-001", channel="Slack", timestamp="2026-06-08 09:14", raw_text="hi"
    )


def test_valid_classification_builds_record():
    classification = Classification.model_validate(
        {
            "category": "автоматизація",
            "priority": "high",
            "short_summary": "test",
            "requested_actions": ["1. do a thing"],
            "needs_clarification": False,
            "confidence": 0.9,
            "urgency_signals": ["терміново"],
            "is_actionable": True,
            "estimated_effort": "medium",
        }
    )
    record = ClassifiedRequest(
        **_request().model_dump(), **classification.model_dump()
    )
    assert record.category is Category.AUTOMATION
    assert record.classification_error is None


def test_fallback_record_is_safe():
    record = ClassifiedRequest.fallback(_request(), "boom")
    assert record.needs_clarification is True
    assert record.category is Category.OUT_OF_SCOPE
    assert record.classification_error == "boom"
    assert record.id == "REQ-001"
