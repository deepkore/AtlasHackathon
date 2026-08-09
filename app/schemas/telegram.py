from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    id: int
    is_bot: bool | None = None
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


class TelegramChat(BaseModel):
    id: int
    type: str


class TelegramMessage(BaseModel):
    message_id: int
    from_user: TelegramUser | None = Field(default=None, alias="from")
    chat: TelegramChat
    text: str | None = None

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class TelegramUpdate(BaseModel):
    update_id: int
    message: TelegramMessage | None = None

    model_config = ConfigDict(extra="ignore")

    def inbound_text(self) -> str | None:
        if self.message is None:
            return None
        return self.message.text

    def sender(self) -> TelegramUser | None:
        if self.message is None:
            return None
        return self.message.from_user

    def chat_id(self) -> int | None:
        if self.message is None:
            return None
        return self.message.chat.id
