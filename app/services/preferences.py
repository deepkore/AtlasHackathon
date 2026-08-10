import pytz
from app.database.models import UserPreference
from app.database.repositories import UserPreferenceRepository


class PreferenceService:
    def __init__(self, repository: UserPreferenceRepository):
        self.repository = repository

    async def get_preferences(self, user_id: int) -> UserPreference | None:
        return await self.repository.get_by_user_id(user_id)

    async def update_preferences(self, user_id: int, **kwargs) -> UserPreference:
        if "timezone" in kwargs and kwargs["timezone"]:
            tz = kwargs["timezone"]
            try:
                pytz.timezone(tz)
            except pytz.UnknownTimeZoneError:
                raise ValueError(f"Invalid timezone: {tz}")
        return await self.repository.upsert(user_id, **kwargs)

    async def add_interest(self, user_id: int, interest: str) -> UserPreference:
        pref = await self.repository.get_by_user_id(user_id)
        interests = pref.interests if pref else []
        interest_clean = interest.strip()
        if not interest_clean:
            return await self.repository.upsert(user_id)
        if not any(i.lower() == interest_clean.lower() for i in interests):
            interests.append(interest_clean)
        return await self.repository.upsert(user_id, interests=interests)

    async def remove_interest(self, user_id: int, interest: str) -> UserPreference:
        pref = await self.repository.get_by_user_id(user_id)
        interests = pref.interests if pref else []
        interest_clean = interest.strip().lower()
        new_interests = [i for i in interests if i.lower() != interest_clean]
        return await self.repository.upsert(user_id, interests=new_interests)
