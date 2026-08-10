from typing import Any
from app.agent.tools import ToolDefinition
from app.services.preferences import PreferenceService


def build_preference_tools(preference_service: PreferenceService) -> list[ToolDefinition]:
    async def get_user_preferences(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        pref = await preference_service.get_preferences(user_id)
        if not pref:
            return {"message": "You have no saved preferences yet."}
        return {
            "role": pref.role,
            "interests": pref.interests,
            "notification_time": pref.notification_time,
            "timezone": pref.timezone,
        }

    async def update_user_preferences(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        update_args = {}
        if "role" in arguments:
            update_args["role"] = arguments["role"]
        if "interests" in arguments:
            update_args["interests"] = arguments["interests"]
        
        await preference_service.update_preferences(user_id, **update_args)
        return {"message": "Preferences updated successfully."}

    async def add_user_interest(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        interest = arguments.get("interest")
        if not interest:
            return {"error": True, "message": "Interest is required."}
        await preference_service.add_interest(user_id, interest)
        return {"message": f"Added '{interest}' to interests."}

    async def remove_user_interest(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        interest = arguments.get("interest")
        if not interest:
            return {"error": True, "message": "Interest is required."}
        await preference_service.remove_interest(user_id, interest)
        return {"message": f"Removed '{interest}' from interests."}

    return [
        ToolDefinition(
            "get_user_preferences",
            "Retrieve the user's saved preferences (role, interests, timezone).",
            {"type": "object", "properties": {}},
            get_user_preferences
        ),
        ToolDefinition(
            "update_user_preferences",
            "Update the user's role or interests. Provide only the fields you wish to change.",
            {
                "type": "object", 
                "properties": {
                    "role": {"type": "string", "description": "The user's professional role or context"},
                    "interests": {"type": "array", "items": {"type": "string"}, "description": "List of interests or topics"}
                }
            },
            update_user_preferences
        ),
        ToolDefinition(
            "add_user_interest",
            "Add a single interest or topic to the user's preferences.",
            {
                "type": "object",
                "properties": {"interest": {"type": "string", "description": "The interest to add"}},
                "required": ["interest"]
            },
            add_user_interest
        ),
        ToolDefinition(
            "remove_user_interest",
            "Remove a single interest or topic from the user's preferences.",
            {
                "type": "object",
                "properties": {"interest": {"type": "string", "description": "The interest to remove"}},
                "required": ["interest"]
            },
            remove_user_interest
        )
    ]
