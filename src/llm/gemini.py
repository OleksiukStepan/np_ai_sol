from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import errors, types

from src.llm.base import LLMProvider
from src.models import Classification
from src.prompt import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

_MAX_RETRIES = 6
_BASE_BACKOFF_SECONDS = 5
# Transient HTTP codes worth retrying: rate limit + temporary server errors.
_RETRYABLE_CODES = {429, 500, 503}


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required to use GeminiProvider")
        self._client = genai.Client(api_key=api_key)
        self._model = model
        # The Pydantic model doubles as the enforced response schema.
        self._config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            response_mime_type="application/json",
            response_schema=Classification,
        )

    async def classify(self, raw_text: str) -> str:
        prompt = build_user_prompt(raw_text)
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model, contents=prompt, config=self._config
                )
                return response.text
            except errors.APIError as err:
                if err.code not in _RETRYABLE_CODES or attempt == _MAX_RETRIES:
                    raise
                delay = _BASE_BACKOFF_SECONDS * 2 ** (attempt - 1)
                logger.warning(
                    "Transient %s, retry %d/%d in %ds",
                    err.code,
                    attempt,
                    _MAX_RETRIES,
                    delay,
                )
                await asyncio.sleep(delay)
