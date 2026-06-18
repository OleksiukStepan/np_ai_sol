from __future__ import annotations

import asyncio
import json
import logging

from pydantic import ValidationError

from src.llm.base import LLMProvider
from src.models import ClassifiedRequest, Classification, InboxRequest

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 2  # initial try + one retry


async def classify_one(
    provider: LLMProvider, request: InboxRequest
) -> ClassifiedRequest:
    """Classify a single request, never raising: bad output becomes a fallback."""
    last_error = ""

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw = await provider.classify(request.raw_text)
            data = json.loads(raw)
            classification = Classification.model_validate(data)
            return ClassifiedRequest(
                **request.model_dump(), **classification.model_dump()
            )
        except (json.JSONDecodeError, ValidationError) as err:
            last_error = f"{type(err).__name__}: {err}"
            logger.warning(
                "Invalid LLM output for %s (attempt %d/%d): %s",
                request.id,
                attempt,
                MAX_ATTEMPTS,
                last_error,
            )
        except Exception as err:  # network / provider errors
            last_error = f"{type(err).__name__}: {err}"
            logger.error("LLM call failed for %s: %s", request.id, last_error)
            break

    return ClassifiedRequest.fallback(request, last_error)


async def classify_all(
    provider: LLMProvider,
    requests: list[InboxRequest],
    concurrency: int = 5,
    use_async: bool = True,
) -> list[ClassifiedRequest]:
    """Classify all requests, async with a concurrency cap or strictly sequential."""
    if not use_async:
        results: list[ClassifiedRequest] = []
        for request in requests:
            results.append(await classify_one(provider, request))
        return results

    semaphore = asyncio.Semaphore(concurrency)

    async def _guarded(request: InboxRequest) -> ClassifiedRequest:
        async with semaphore:
            return await classify_one(provider, request)

    return await asyncio.gather(*(_guarded(req) for req in requests))
