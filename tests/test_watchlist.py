import pytest
from app.database.models import User
from app.database.repositories import WatchlistRepository
from app.services.watchlist import WatchlistService

@pytest.fixture
async def watchlist_service(test_session):
    repo = WatchlistRepository(test_session)
    return WatchlistService(repo)

@pytest.fixture
async def test_user(test_session):
    user = User(telegram_user_id=123, username="test_user")
    test_session.add(user)
    await test_session.flush()
    return user

async def test_add_and_get_watchlist(watchlist_service, test_user, test_session):
    await watchlist_service.add_to_watchlist(test_user.id, "nvda", "Nvidia")
    await test_session.commit()
    
    items = await watchlist_service.get_watchlist(test_user.id)
    assert len(items) == 1
    assert items[0].symbol == "NVDA"
    assert items[0].company_name == "Nvidia"

async def test_add_duplicate(watchlist_service, test_user, test_session):
    await watchlist_service.add_to_watchlist(test_user.id, "NVDA")
    await watchlist_service.add_to_watchlist(test_user.id, "nvda")
    await test_session.commit()
    
    items = await watchlist_service.get_watchlist(test_user.id)
    assert len(items) == 1

async def test_remove_from_watchlist(watchlist_service, test_user, test_session):
    await watchlist_service.add_to_watchlist(test_user.id, "MSFT")
    await watchlist_service.add_to_watchlist(test_user.id, "AAPL")
    removed = await watchlist_service.remove_from_watchlist(test_user.id, "msft")
    await test_session.commit()
    
    assert removed is True
    items = await watchlist_service.get_watchlist(test_user.id)
    assert len(items) == 1
    assert items[0].symbol == "AAPL"

async def test_clear_watchlist(watchlist_service, test_user, test_session):
    await watchlist_service.add_to_watchlist(test_user.id, "MSFT")
    await watchlist_service.add_to_watchlist(test_user.id, "AAPL")
    count = await watchlist_service.clear_watchlist(test_user.id)
    await test_session.commit()
    
    assert count == 2
    items = await watchlist_service.get_watchlist(test_user.id)
    assert len(items) == 0

async def test_user_isolation(watchlist_service, test_session):
    user1 = User(telegram_user_id=1, username="user1")
    user2 = User(telegram_user_id=2, username="user2")
    test_session.add(user1)
    test_session.add(user2)
    await test_session.flush()

    await watchlist_service.add_to_watchlist(user1.id, "AAPL")
    await watchlist_service.add_to_watchlist(user2.id, "MSFT")
    await test_session.commit()
    
    items1 = await watchlist_service.get_watchlist(user1.id)
    items2 = await watchlist_service.get_watchlist(user2.id)
    
    assert len(items1) == 1
    assert items1[0].symbol == "AAPL"
    
    assert len(items2) == 1
    assert items2[0].symbol == "MSFT"
