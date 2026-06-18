from src.classifier import classify_all, classify_one
from src.llm.base import LLMProvider
from src.models import InboxRequest

VALID_JSON = (
    '{"category": "інтеграція", "target_department": "support", '
    '"priority": "high", "short_summary": "s", "requested_actions": ["1. a"], '
    '"needs_clarification": false, "confidence": 0.8, '
    '"urgency_signals": [], "is_actionable": true, "estimated_effort": "low"}'
)


class StubProvider(LLMProvider):
    def __init__(self, payload: str):
        self.payload = payload

    async def classify(self, raw_text: str) -> str:
        return self.payload


def _req(req_id: str = "REQ-1") -> InboxRequest:
    return InboxRequest(id=req_id, channel="Slack", timestamp="t", raw_text="x")


async def test_valid_output_classified():
    record = await classify_one(StubProvider(VALID_JSON), _req())
    assert record.classification_error is None
    assert record.category.value == "інтеграція"


async def test_invalid_json_falls_back():
    record = await classify_one(StubProvider("not json"), _req())
    assert record.classification_error is not None
    assert record.needs_clarification is True


async def test_missing_field_falls_back():
    record = await classify_one(StubProvider('{"category": "інтеграція"}'), _req())
    assert record.classification_error is not None


async def test_classify_all_async_preserves_count():
    requests = [_req(f"REQ-{i}") for i in range(5)]
    results = await classify_all(StubProvider(VALID_JSON), requests, concurrency=2)
    assert len(results) == 5
