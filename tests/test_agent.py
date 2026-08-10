from app.agent.agent import Agent
from app.llm.base import LLMProvider
from app.schemas.agent import ConversationMessage, LLMResponse, ToolCall
from app.services.conversation import ConversationService


class FakeLLM(LLMProvider):
    def __init__(self):
        self.calls = 0
        self.messages = []

    async def generate(self, messages: list[ConversationMessage]) -> LLMResponse:
        self.calls += 1
        return LLMResponse(content="Retrieved facts: NVDA quote is available. Analysis: price is up.", tool_calls=[])

    async def generate_with_tools(self, messages: list[ConversationMessage], tools: list[dict]) -> LLMResponse:
        self.calls += 1
        self.messages.append(messages)
        if self.calls == 1:
            return LLMResponse(content="", tool_calls=[ToolCall(name="get_stock_quote", arguments={"symbol": "NVDA"})])
        return LLMResponse(content="Retrieved facts: NVDA quote is available. Analysis: price is up.", tool_calls=[])


class MultiToolLLM(LLMProvider):
    def __init__(self):
        self.calls = 0
        self.messages = []

    async def generate(self, messages: list[ConversationMessage]) -> LLMResponse:
        raise AssertionError("agent should use generate_with_tools for the loop")

    async def generate_with_tools(self, messages: list[ConversationMessage], tools: list[dict]) -> LLMResponse:
        self.calls += 1
        self.messages.append(messages)
        if self.calls == 1:
            return LLMResponse(content="", tool_calls=[ToolCall(name="get_stock_quote", arguments={"symbol": "NVDA"})])
        if self.calls == 2:
            return LLMResponse(content="", tool_calls=[ToolCall(name="get_company_news", arguments={"symbol": "NVDA"})])
        return LLMResponse(content="NVDA rose after current quote and news checks.", tool_calls=[])


class LoopingLLM(LLMProvider):
    async def generate(self, messages: list[ConversationMessage]) -> LLMResponse:
        raise AssertionError("agent should use generate_with_tools for the loop")

    async def generate_with_tools(self, messages: list[ConversationMessage], tools: list[dict]) -> LLMResponse:
        return LLMResponse(content="", tool_calls=[ToolCall(name="get_stock_quote", arguments={"symbol": "NVDA"})])


class FakeTool:
    name = "get_stock_quote"
    description = "Fake quote tool"
    parameters = {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}

    def declaration(self):
        return {"name": self.name, "description": self.description, "parameters": self.parameters}

    async def run(self, arguments, user_id):
        return {"symbol": arguments["symbol"], "source": "test", "data": {"c": 100}}


class FakeNewsTool:
    name = "get_company_news"
    description = "Fake news tool"
    parameters = {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]}

    def declaration(self):
        return {"name": self.name, "description": self.description, "parameters": self.parameters}

    async def run(self, arguments, user_id):
        return {"symbol": arguments["symbol"], "articles": [{"headline": "Good news"}]}


async def test_agent_flow(test_session):
    from app.database.repositories import MessageRepository, UserRepository, UserPreferenceRepository, WatchlistRepository
    from app.schemas.telegram import TelegramUser
    from app.services.preferences import PreferenceService
    from app.services.watchlist import WatchlistService

    user = await UserRepository(test_session).get_or_create_from_telegram(TelegramUser(id=777))
    conversation_service = ConversationService(MessageRepository(test_session), context_limit=5)
    preference_service = PreferenceService(UserPreferenceRepository(test_session))
    watchlist_service = WatchlistService(WatchlistRepository(test_session))
    
    agent = Agent(
        llm_provider=FakeLLM(), 
        conversation_service=conversation_service, 
        preference_service=preference_service,
        watchlist_service=watchlist_service,
        tools=[FakeTool()]
    )

    response = await agent.respond(user_id=user.id, message="Tell me about NVDA")

    assert "Retrieved facts" in response
    messages = await MessageRepository(test_session).latest_for_user(user_id=user.id, limit=10)
    assert [message.role for message in messages] == ["user", "assistant"]


async def test_agent_multiple_sequential_tool_calls(test_session):
    from app.database.repositories import MessageRepository, UserRepository, UserPreferenceRepository, WatchlistRepository
    from app.schemas.telegram import TelegramUser
    from app.services.preferences import PreferenceService
    from app.services.watchlist import WatchlistService

    user = await UserRepository(test_session).get_or_create_from_telegram(TelegramUser(id=778))
    conversation_service = ConversationService(MessageRepository(test_session), context_limit=5)
    preference_service = PreferenceService(UserPreferenceRepository(test_session))
    watchlist_service = WatchlistService(WatchlistRepository(test_session))
    llm = MultiToolLLM()
    
    agent = Agent(
        llm_provider=llm, 
        conversation_service=conversation_service, 
        preference_service=preference_service,
        watchlist_service=watchlist_service,
        tools=[FakeTool(), FakeNewsTool()]
    )

    response = await agent.respond(user_id=user.id, message="Why is NVDA up?")

    assert response == "NVDA rose after current quote and news checks."
    assert llm.calls == 3
    assert [message.tool_name for message in llm.messages[-1] if message.role == "tool"] == [
        "get_stock_quote",
        "get_company_news",
    ]


async def test_agent_max_tool_iteration_protection(test_session):
    from app.database.repositories import MessageRepository, UserRepository, UserPreferenceRepository, WatchlistRepository
    from app.schemas.telegram import TelegramUser
    from app.services.preferences import PreferenceService
    from app.services.watchlist import WatchlistService

    user = await UserRepository(test_session).get_or_create_from_telegram(TelegramUser(id=779))
    conversation_service = ConversationService(MessageRepository(test_session), context_limit=5)
    preference_service = PreferenceService(UserPreferenceRepository(test_session))
    watchlist_service = WatchlistService(WatchlistRepository(test_session))
    
    agent = Agent(
        llm_provider=LoopingLLM(),
        conversation_service=conversation_service,
        preference_service=preference_service,
        watchlist_service=watchlist_service,
        tools=[FakeTool()],
        max_tool_calls=2,
    )

    response = await agent.respond(user_id=user.id, message="Keep checking NVDA")

    assert "tool-use limit" in response
