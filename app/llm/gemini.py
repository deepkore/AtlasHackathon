import asyncio
import json
import logging
import warnings
from typing import Any

warnings.filterwarnings("ignore", message=".*MALFORMED_RESPONSE.*", category=UserWarning)

from google import genai
from google.genai import types

from app.llm.base import LLMProvider
from app.schemas.agent import ConversationMessage, LLMResponse, ToolCall

logger = logging.getLogger(__name__)


class GeminiError(RuntimeError):
    pass


class GeminiProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate(self, messages: list[ConversationMessage]) -> LLMResponse:
        return await self.generate_with_tools(messages, tools=[])

    async def generate_with_tools(self, messages: list[ConversationMessage], tools: list[dict]) -> LLMResponse:
        try:
            response = await asyncio.to_thread(self._generate_sync, messages, tools)
        except Exception as exc:
            logger.exception("Gemini generation failed")
            raise GeminiError("LLM response is unavailable") from exc
        return response
        
    async def generate_structured(self, messages: list[ConversationMessage], schema: type) -> Any:
        try:
            return await asyncio.to_thread(self._generate_structured_sync, messages, schema)
        except Exception as exc:
            logger.exception("Gemini structured generation failed")
            raise GeminiError("LLM structured response is unavailable") from exc

    def _generate_sync(self, messages: list[ConversationMessage], tools: list[dict]) -> LLMResponse:
        system_text = "\n\n".join(message.content for message in messages if message.role == "system")
        contents = [
            self._message_to_content(message)
            for message in messages
            if message.role != "system"
        ]
        config_kwargs: dict[str, Any] = {}
        if system_text:
            config_kwargs["system_instruction"] = system_text
        if tools:
            config_kwargs["tools"] = [types.Tool(function_declarations=[self._tool_to_declaration(tool) for tool in tools])]

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        tool_calls: list[ToolCall] = []
        text_parts: list[str] = []
        candidates = response.candidates or []
        for candidate in candidates:
            if not candidate.content or not candidate.content.parts:
                continue
            for part in candidate.content.parts:
                if getattr(part, "function_call", None):
                    function_call = part.function_call
                    tool_calls.append(ToolCall(name=function_call.name, arguments=dict(function_call.args or {})))
                elif getattr(part, "text", None):
                    text_parts.append(part.text)

        return LLMResponse(content="\n".join(text_parts).strip(), tool_calls=tool_calls)

    def _generate_structured_sync(self, messages: list[ConversationMessage], schema: type) -> Any:
        system_text = "\n\n".join(message.content for message in messages if message.role == "system")
        contents = [
            self._message_to_content(message)
            for message in messages
            if message.role != "system"
        ]
        config_kwargs: dict[str, Any] = {
            "response_mime_type": "application/json",
            "response_schema": schema
        }
        if system_text:
            config_kwargs["system_instruction"] = system_text

        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )
        
        if not response.text:
            raise GeminiError("Empty structured response")
            
        try:
            return schema.model_validate_json(response.text)
        except Exception as exc:
            logger.error("Failed to parse structured LLM response: %s", response.text)
            raise GeminiError("Invalid structured response format") from exc

    @staticmethod
    def _tool_to_declaration(tool: dict) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=tool["name"],
            description=tool.get("description", ""),
            parameters=tool.get("parameters", {}),
        )

    @staticmethod
    def _message_to_content(message: ConversationMessage) -> types.Content:
        if message.role == "tool" and message.tool_name:
            try:
                payload = json.loads(message.content)
            except Exception:
                payload = {"result": message.content}
            return types.Content(
                role="user",
                parts=[types.Part.from_function_response(name=message.tool_name, response=payload)],
            )
        return types.Content(
            role="model" if message.role == "assistant" else "user",
            parts=[types.Part(text=message.content)],
        )
