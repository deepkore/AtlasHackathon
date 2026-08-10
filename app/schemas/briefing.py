from pydantic import BaseModel, Field


class BriefingItem(BaseModel):
    title: str = Field(description="The headline or title of the event/news.")
    summary: str = Field(description="A brief summary of what happened.")
    why_it_matters: str = Field(description="Why this is specifically important to the user or the market.")
    source: str = Field(description="The source of the information (e.g., Reuters, SEC, Finnhub).")
    source_url: str | None = Field(default=None, description="The URL of the source article or filing, if available.")


class BriefingDecision(BaseModel):
    should_send: bool = Field(description="Whether this briefing contains genuinely meaningful information that warrants sending a notification.")
    importance_score: float = Field(description="A score between 0.0 and 1.0 indicating the overall importance of the aggregated information.")
    reason: str = Field(description="The reasoning behind the should_send decision.")
    items: list[BriefingItem] = Field(default_factory=list, description="The meaningful items to include in the briefing.")
