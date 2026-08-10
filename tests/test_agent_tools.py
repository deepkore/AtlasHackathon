import pytest
from app.agent.preference_tools import build_preference_tools
from app.agent.tools import ToolRegistry
from app.agent.watchlist_tools import build_watchlist_tools
from app.database.models import User
from app.database.repositories import UserPreferenceRepository, WatchlistRepository
from app.services.preferences import PreferenceService
from app.services.watchlist import WatchlistService

@pytest.fixture
async def test_user(test_session):
    user = User(telegram_user_id=123, username="test_user")
    test_session.add(user)
    await test_session.flush()
    return user

@pytest.fixture
def registry(test_session):
    pref_service = PreferenceService(UserPreferenceRepository(test_session))
    watch_service = WatchlistService(WatchlistRepository(test_session))
    
    registry = ToolRegistry()
    for tool in build_preference_tools(pref_service):
        registry.register(tool)
    for tool in build_watchlist_tools(watch_service):
        registry.register(tool)
    return registry

async def test_preference_tools(registry, test_user, test_session):
    # Get empty pref
    res = await registry.execute("get_user_preferences", {}, "r1", test_user.id)
    assert "no saved preferences" in res["message"]
    
    # Update role
    await registry.execute("update_user_preferences", {"role": "Analyst"}, "r1", test_user.id)
    await test_session.commit()
    
    res = await registry.execute("get_user_preferences", {}, "r1", test_user.id)
    assert res["role"] == "Analyst"
    
    # Add interest
    await registry.execute("add_user_interest", {"interest": "AI"}, "r1", test_user.id)
    await test_session.commit()
    
    res = await registry.execute("get_user_preferences", {}, "r1", test_user.id)
    assert res["interests"] == ["AI"]
    
    # Remove interest
    await registry.execute("remove_user_interest", {"interest": "ai"}, "r1", test_user.id)
    await test_session.commit()
    
    res = await registry.execute("get_user_preferences", {}, "r1", test_user.id)
    assert res["interests"] == []

async def test_watchlist_tools(registry, test_user, test_session):
    # Get empty
    res = await registry.execute("get_watchlist", {}, "r1", test_user.id)
    assert "empty" in res["message"]
    
    # Add
    await registry.execute("add_to_watchlist", {"symbol": "nvda", "company_name": "Nvidia"}, "r1", test_user.id)
    await test_session.commit()
    
    res = await registry.execute("get_watchlist", {}, "r1", test_user.id)
    assert len(res["watchlist"]) == 1
    assert res["watchlist"][0]["symbol"] == "NVDA"
    
    # Remove
    await registry.execute("remove_from_watchlist", {"symbol": "NVDA"}, "r1", test_user.id)
    await test_session.commit()
    
    res = await registry.execute("get_watchlist", {}, "r1", test_user.id)
    assert "empty" in res["message"]

    # Clear
    await registry.execute("add_to_watchlist", {"symbol": "MSFT"}, "r1", test_user.id)
    await registry.execute("add_to_watchlist", {"symbol": "AAPL"}, "r1", test_user.id)
    await registry.execute("clear_watchlist", {}, "r1", test_user.id)
    await test_session.commit()

    res = await registry.execute("get_watchlist", {}, "r1", test_user.id)
    assert "empty" in res["message"]
