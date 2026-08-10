import json
import logging
import uuid

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import ToolDefinition, ToolRegistry
from app.llm.base import LLMProvider
from app.schemas.agent import ConversationMessage
from app.services.conversation import ConversationService
from app.services.preferences import PreferenceService
from app.services.watchlist import WatchlistService

logger = logging.getLogger(__name__)


class Agent:
    def __init__(
        self,
        llm_provider: LLMProvider,
        conversation_service: ConversationService,
        preference_service: PreferenceService,
        watchlist_service: WatchlistService,
        tools: list[ToolDefinition] | ToolRegistry,
        max_tool_calls: int = 8,
    ):
        self.llm_provider = llm_provider
        self.conversation_service = conversation_service
        self.preference_service = preference_service
        self.watchlist_service = watchlist_service
        self.tool_registry = tools if isinstance(tools, ToolRegistry) else self._registry_from_tools(tools)
        self.max_tool_calls = max_tool_calls

    async def respond(self, user_id: int, message: str) -> str:
        request_id = str(uuid.uuid4())
        await self.conversation_service.add_user_message(user_id=user_id, content=message)
        context = await self.conversation_service.get_context(user_id=user_id)
        
        pref = await self.preference_service.get_preferences(user_id)
        watchlist = await self.watchlist_service.get_watchlist(user_id)
        
        system_context_msg = self._build_system_context(pref, watchlist)
        messages = [
            ConversationMessage(role="system", content=SYSTEM_PROMPT), 
            ConversationMessage(role="system", content=system_context_msg),
            *context
        ]
        tool_call_count = 0

        response = await self.llm_provider.generate_with_tools(messages=messages, tools=self.tool_registry.declarations())
        while response.tool_calls:
            if tool_call_count >= self.max_tool_calls:
                content = "I reached the tool-use limit before I could finish the research. Please narrow the request and try again."
                break
            messages.append(
                ConversationMessage(
                    role="assistant",
                    content=response.content or "I need to retrieve external financial data before answering.",
                )
            )
            for call in response.tool_calls:
                if tool_call_count >= self.max_tool_calls:
                    break
                result = await self.tool_registry.execute(call.name, call.arguments, request_id=request_id, user_id=user_id)
                tool_call_count += 1
                messages.append(
                    ConversationMessage(
                        role="tool",
                        tool_name=call.name,
                        content=json.dumps({"tool": call.name, "result": result}, default=str),
                    )
                )
            response = await self.llm_provider.generate_with_tools(messages=messages, tools=self.tool_registry.declarations())
        else:
            content = response.content

        logger.info(
            "agent_request_completed",
            extra={"user_id": user_id, "agent_request_id": request_id, "tool_call_count": tool_call_count},
        )

        response_text = content.strip() if content and content.strip() else "I couldn't generate a useful response right now."
        await self.conversation_service.add_assistant_message(user_id=user_id, content=response_text)
        return response_text

    @staticmethod
    def _build_system_context(pref, watchlist) -> str:
        context_data = {}
        if pref:
            context_data["preferences"] = {
                "role": pref.role,
                "interests": pref.interests,
                "timezone": pref.timezone,
            }
        else:
            context_data["preferences"] = None
            
        if watchlist:
            context_data["watchlist"] = [
                {"symbol": item.symbol, "company_name": item.company_name} 
                for item in watchlist
            ]
        else:
            context_data["watchlist"] = []
            
        return f"SYSTEM/CONTEXT:\nUser profile information:\n{json.dumps(context_data, indent=2)}"

    @staticmethod
    def _registry_from_tools(tools: list[ToolDefinition]) -> ToolRegistry:
        registry = ToolRegistry()
        for tool in tools:
            registry.register(tool)
        return registry
