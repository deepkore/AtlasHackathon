import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.agent.scheduling_tools import build_scheduling_tools
from app.database.models import ScheduledTask

@pytest.fixture
def mock_task_repo():
    repo = AsyncMock()
    return repo

@pytest.fixture
def scheduling_tools(mock_task_repo):
    tools = build_scheduling_tools(mock_task_repo)
    return {tool.name: tool for tool in tools}

@pytest.mark.asyncio
async def test_get_scheduled_tasks_empty(scheduling_tools, mock_task_repo):
    mock_task_repo.get_by_user_id.return_value = []
    
    tool = scheduling_tools["get_scheduled_tasks"]
    result = await tool.run({}, 1)
    
    assert result["status"] == "success"
    assert len(result["tasks"]) == 0

@pytest.mark.asyncio
async def test_create_scheduled_task(scheduling_tools, mock_task_repo):
    task = ScheduledTask(id=1, user_id=1, task_type="morning_briefing", schedule={}, next_run_at=None)
    mock_task_repo.create.return_value = task
    
    tool = scheduling_tools["create_scheduled_task"]
    
    with patch("app.services.scheduler.Scheduler._calculate_next_run", return_value=None):
        result = await tool.run({"task_type": "morning_briefing", "frequency": "daily", "time": "08:30"}, 1)
        
    assert result["status"] == "success"
    assert result["task_id"] == 1
    mock_task_repo.create.assert_called_once()
