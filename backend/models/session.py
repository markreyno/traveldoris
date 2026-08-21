from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from backend.models.research import ResearchResult
from backend.models.trip import ConversationMessage, DorisParserResult, TripRequest


class TripSession(BaseModel):
    id: str
    created_at: str
    updated_at: str
    messages: list[ConversationMessage] = Field(default_factory=list)
    trip: Optional[TripRequest] = None
    intake: Optional[DorisParserResult] = None
    research_confirmed: bool = False
    deferred_fields_accepted: bool = False
    research: Optional[ResearchResult] = None


class CreateTripSessionRequest(BaseModel):
    pass


class AddTripMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)


class StartResearchRequest(BaseModel):
    confirmed: bool
    accept_deferred_fields: bool = False
