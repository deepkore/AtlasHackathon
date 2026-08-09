from typing import Any, Literal

from pydantic import BaseModel


class ConversationMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_name: str | None = None


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any]


class LLMResponse(BaseModel):
    content: str
    tool_calls: list[ToolCall] = []
