import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.database.models import ScheduledTask
from app.services.scheduler import Scheduler

@pytest.fixture
def sample_task():
    return ScheduledTask(
        id=1,
        user_id=1,
        task_type="morning_briefing",
        schedule={"frequency": "daily", "time": "08:30"},
        timezone="America/New_York",
        enabled=True
    )

def test_calculate_next_run_daily(sample_task):
    scheduler = Scheduler()
    
    # Mock current time as 07:00 NY time
    tz = ZoneInfo("America/New_York")
    now_local = datetime(2023, 10, 1, 7, 0, tzinfo=tz) # 7:00 AM NY time
    now_utc = now_local.astimezone(timezone.utc)
    
    next_run = scheduler._calculate_next_run(sample_task, now_utc)
    next_run_local = next_run.astimezone(tz)
    
    assert next_run_local.hour == 8
    assert next_run_local.minute == 30
    assert next_run_local.day == 1

def test_calculate_next_run_daily_next_day(sample_task):
    scheduler = Scheduler()
    
    # Mock current time as 09:00 NY time
    tz = ZoneInfo("America/New_York")
    now_local = datetime(2023, 10, 1, 9, 0, tzinfo=tz) # 9:00 AM NY time
    now_utc = now_local.astimezone(timezone.utc)
    
    next_run = scheduler._calculate_next_run(sample_task, now_utc)
    next_run_local = next_run.astimezone(tz)
    
    assert next_run_local.hour == 8
    assert next_run_local.minute == 30
    assert next_run_local.day == 2

def test_calculate_next_run_weekdays(sample_task):
    sample_task.schedule["frequency"] = "weekdays"
    scheduler = Scheduler()
    
    # Mock current time as Friday 09:00 NY time
    tz = ZoneInfo("America/New_York")
    # 2023-10-06 is Friday
    now_local = datetime(2023, 10, 6, 9, 0, tzinfo=tz)
    now_utc = now_local.astimezone(timezone.utc)
    
    next_run = scheduler._calculate_next_run(sample_task, now_utc)
    next_run_local = next_run.astimezone(tz)
    
    # Next run should be Monday
    assert next_run_local.hour == 8
    assert next_run_local.minute == 30
    assert next_run_local.day == 9 # 6 + 3 = 9
