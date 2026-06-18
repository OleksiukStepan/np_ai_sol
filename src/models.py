from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Category(str, Enum):
    AUTOMATION = "автоматизація"
    INTEGRATION = "інтеграція"
    REPORT_ANALYTICS = "звіт/аналітика"
    BUG_SUPPORT = "баг/підтримка"
    QUESTION_CONSULT = "питання/консультація"
    OUT_OF_SCOPE = "поза скоупом"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EstimatedEffort(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InboxRequest(BaseModel):
    """One raw row from the input inbox CSV."""

    id: str
    channel: str
    timestamp: str
    raw_text: str


class Classification(BaseModel):
    """Structured fields the LLM must return. This is the strict validation target."""

    category: Category
    target_department: str | None = Field(
        default=None, description="Requesting department, or null if unclear"
    )
    priority: Priority
    short_summary: str = Field(description="One-sentence essence of the request")
    requested_actions: list[str] = Field(
        default_factory=list,
        description="Numbered concrete actions asked for (0, 1 or many)",
    )
    needs_clarification: bool = Field(
        description="True if the request is too vague to act on as-is"
    )
    # Schema extensions (justified in README)
    confidence: float = Field(ge=0.0, le=1.0, description="Model confidence 0..1")
    urgency_signals: list[str] = Field(
        default_factory=list,
        description="Tone/deadline words that drove priority",
    )
    is_actionable: bool = Field(
        description="False when the message is not a task (e.g. a thank-you note)"
    )
    estimated_effort: EstimatedEffort = Field(
        description="Rough time effort to deliver: low/medium/high"
    )


class ClassifiedRequest(InboxRequest, Classification):
    """Final record: input fields + classification + optional error marker."""

    classification_error: str | None = Field(
        default=None, description="Set only when the fallback record was produced"
    )

    @classmethod
    def fallback(cls, request: InboxRequest, error: str) -> "ClassifiedRequest":
        """Build a safe record when the LLM output could not be validated."""
        return cls(
            **request.model_dump(),
            category=Category.OUT_OF_SCOPE,
            target_department=None,
            priority=Priority.LOW,
            short_summary="(не вдалося класифікувати автоматично)",
            requested_actions=[],
            needs_clarification=True,
            confidence=0.0,
            urgency_signals=[],
            is_actionable=False,
            estimated_effort=EstimatedEffort.LOW,
            classification_error=error,
        )
