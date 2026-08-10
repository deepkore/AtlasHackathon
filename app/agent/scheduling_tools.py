import json
import logging
from typing import Any
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.database.repositories import ScheduledTaskRepository
from app.agent.tools import ToolDefinition

logger = logging.getLogger(__name__)

def build_scheduling_tools(task_repo: ScheduledTaskRepository) -> list[ToolDefinition]:

    def _string_arg(arguments: dict[str, Any], key: str) -> str:
        value = arguments.get(key)
        return str(value).strip() if value is not None else ""

    def _missing(message: str) -> dict[str, Any]:
        return {"error": True, "message": message}

    async def get_scheduled_tasks(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        tasks = await task_repo.get_by_user_id(user_id)
        if not tasks:
            return {"status": "success", "message": "You have no scheduled tasks.", "tasks": []}
            
        return {
            "status": "success",
            "tasks": [
                {
                    "id": t.id,
                    "task_type": t.task_type,
                    "schedule": t.schedule,
                    "timezone": t.timezone,
                    "enabled": t.enabled,
                    "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None
                } for t in tasks
            ]
        }

    async def create_scheduled_task(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        task_type = _string_arg(arguments, "task_type")
        frequency = _string_arg(arguments, "frequency")
        time_str = _string_arg(arguments, "time")
        tz = _string_arg(arguments, "timezone") or "UTC"
        
        if not task_type or not frequency or not time_str:
            return _missing("task_type, frequency, and time are required.")
            
        schedule = {"frequency": frequency, "time": time_str}
        
        task = await task_repo.create(user_id, task_type, schedule, tz)
        
        # Calculate initial next_run_at
        now = datetime.now(timezone.utc)
        try:
            from app.services.scheduler import Scheduler
            task.next_run_at = Scheduler()._calculate_next_run(task, now)
            await task_repo.update(task)
        except Exception as e:
            logger.error(f"Failed to set initial next_run_at: {e}")
            
        return {"status": "success", "message": f"Scheduled task created with ID {task.id}.", "task_id": task.id, "next_run_at": task.next_run_at.isoformat() if task.next_run_at else None}

    async def update_scheduled_task(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        task_id = arguments.get("task_id")
        if not task_id:
            return _missing("task_id is required.")
            
        task = await task_repo.get_by_id(task_id, user_id)
        if not task:
            return _missing(f"Task {task_id} not found or doesn't belong to you.")
            
        frequency = _string_arg(arguments, "frequency")
        time_str = _string_arg(arguments, "time")
        tz = _string_arg(arguments, "timezone")
        enabled = arguments.get("enabled")
        
        if frequency:
            task.schedule["frequency"] = frequency
        if time_str:
            task.schedule["time"] = time_str
        if tz:
            task.timezone = tz
        if enabled is not None:
            task.enabled = bool(enabled)
            
        now = datetime.now(timezone.utc)
        from app.services.scheduler import Scheduler
        task.next_run_at = Scheduler()._calculate_next_run(task, now)
            
        await task_repo.update(task)
        
        return {"status": "success", "message": f"Scheduled task {task_id} updated."}

    async def disable_scheduled_task(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        task_id = arguments.get("task_id")
        if not task_id:
            return _missing("task_id is required.")
            
        task = await task_repo.get_by_id(task_id, user_id)
        if not task:
            return _missing(f"Task {task_id} not found.")
            
        task.enabled = False
        await task_repo.update(task)
        
        return {"status": "success", "message": f"Scheduled task {task_id} disabled."}

    async def delete_scheduled_task(arguments: dict[str, Any], user_id: int) -> dict[str, Any]:
        task_id = arguments.get("task_id")
        if not task_id:
            return _missing("task_id is required.")
            
        task = await task_repo.get_by_id(task_id, user_id)
        if not task:
            return _missing(f"Task {task_id} not found.")
            
        await task_repo.delete(task)
        
        return {"status": "success", "message": f"Scheduled task {task_id} deleted."}


    return [
        ToolDefinition(
            "get_scheduled_tasks", 
            "Retrieve all scheduled tasks (briefings, summaries) for the user.",
            {"type": "object", "properties": {}},
            get_scheduled_tasks
        ),
        ToolDefinition(
            "create_scheduled_task",
            "Create a new scheduled task.",
            {
                "type": "object",
                "properties": {
                    "task_type": {"type": "string", "description": "Type of task, e.g. morning_briefing, evening_summary"},
                    "frequency": {"type": "string", "description": "Frequency, e.g. daily, weekdays"},
                    "time": {"type": "string", "description": "Time of day in HH:MM format (24-hour)"},
                    "timezone": {"type": "string", "description": "IANA timezone, e.g. America/New_York"}
                },
                "required": ["task_type", "frequency", "time"]
            },
            create_scheduled_task
        ),
        ToolDefinition(
            "update_scheduled_task",
            "Update an existing scheduled task.",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task to update"},
                    "frequency": {"type": "string", "description": "New frequency, e.g. daily, weekdays"},
                    "time": {"type": "string", "description": "New time in HH:MM format"},
                    "timezone": {"type": "string", "description": "New timezone"},
                    "enabled": {"type": "boolean", "description": "Enable or disable the task"}
                },
                "required": ["task_id"]
            },
            update_scheduled_task
        ),
        ToolDefinition(
            "disable_scheduled_task",
            "Disable an existing scheduled task without deleting it.",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task to disable"}
                },
                "required": ["task_id"]
            },
            disable_scheduled_task
        ),
        ToolDefinition(
            "delete_scheduled_task",
            "Permanently delete a scheduled task.",
            {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "ID of the task to delete"}
                },
                "required": ["task_id"]
            },
            delete_scheduled_task
        )
    ]
