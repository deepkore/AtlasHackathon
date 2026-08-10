import pytest
from app.database.models import User
from app.database.repositories import UserPreferenceRepository
from app.services.preferences import PreferenceService

@pytest.fixture
async def preference_service(test_session):
    repo = UserPreferenceRepository(test_session)
    return PreferenceService(repo)

@pytest.fixture
async def test_user(test_session):
    user = User(telegram_user_id=123, username="test_user")
    test_session.add(user)
    await test_session.flush()
    return user

async def test_create_and_get_preferences(preference_service, test_user, test_session):
    await preference_service.update_preferences(test_user.id, role="Analyst")
    await test_session.commit()
    
    pref = await preference_service.get_preferences(test_user.id)
    assert pref is not None
    assert pref.role == "Analyst"
    assert pref.interests == []

async def test_add_interest(preference_service, test_user, test_session):
    await preference_service.add_interest(test_user.id, "AI")
    await preference_service.add_interest(test_user.id, "Semiconductors")
    await preference_service.add_interest(test_user.id, "ai") # duplicate case-insensitive
    await test_session.commit()
    
    pref = await preference_service.get_preferences(test_user.id)
    assert pref.interests == ["AI", "Semiconductors"]

async def test_remove_interest(preference_service, test_user, test_session):
    await preference_service.add_interest(test_user.id, "AI")
    await preference_service.add_interest(test_user.id, "Cloud")
    await preference_service.remove_interest(test_user.id, "ai")
    await test_session.commit()
    
    pref = await preference_service.get_preferences(test_user.id)
    assert pref.interests == ["Cloud"]

async def test_partial_update(preference_service, test_user, test_session):
    await preference_service.update_preferences(test_user.id, role="Founder", timezone="Asia/Kolkata")
    await preference_service.update_preferences(test_user.id, role="Investor")
    await test_session.commit()
    
    pref = await preference_service.get_preferences(test_user.id)
    assert pref.role == "Investor"
    assert pref.timezone == "Asia/Kolkata"

async def test_invalid_timezone(preference_service, test_user):
    with pytest.raises(ValueError):
        await preference_service.update_preferences(test_user.id, timezone="Invalid/Timezone")
