from unittest.mock import Mock

from app.llm.gemini import GeminiProvider
from app.schemas.agent import ConversationMessage, ToolCall


async def test_gemini_provider_mocked_response(monkeypatch):
    provider = GeminiProvider(api_key="fake", model="gemini-2.5-flash")
    fake_response = Mock()
    fake_response.candidates = []
    fake_response.text = "Hello"

    def fake_generate_sync(messages, tools):
        return type("Response", (), {"content": "Mocked Gemini answer", "tool_calls": []})()

    monkeypatch.setattr(provider, "_generate_sync", fake_generate_sync)

    response = await provider.generate([ConversationMessage(role="user", content="Hi")])

    assert response.content == "Mocked Gemini answer"
    assert response.tool_calls == []


def test_gemini_provider_parses_tool_calls(monkeypatch):
    provider = GeminiProvider(api_key="fake", model="gemini-2.5-flash")
    function_call = Mock()
    function_call.name = "get_stock_quote"
    function_call.args = {"symbol": "NVDA"}
    part = Mock()
    part.function_call = function_call
    part.text = None
    candidate = Mock()
    candidate.content.parts = [part]
    response = Mock()
    response.candidates = [candidate]

    monkeypatch.setattr(provider.client.models, "generate_content", lambda **kwargs: response)

    parsed = provider._generate_sync([ConversationMessage(role="user", content="What is NVDA trading at?")], [])

    assert parsed.tool_calls == [ToolCall(name="get_stock_quote", arguments={"symbol": "NVDA"})]
