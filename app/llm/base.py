from abc import ABC, abstractmethod

from typing import Any
from app.schemas.agent import ConversationMessage, LLMResponse


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: list[ConversationMessage]) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    async def generate_with_tools(self, messages: list[ConversationMessage], tools: list[dict]) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    async def generate_structured(self, messages: list[ConversationMessage], schema: type) -> Any:
        raise NotImplementedError

