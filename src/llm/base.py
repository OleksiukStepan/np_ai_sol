from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):

    @abstractmethod
    async def classify(self, raw_text: str) -> str:
        """Send the request text to the model and return its JSON string."""
        raise NotImplementedError
