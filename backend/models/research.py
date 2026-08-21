from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ResearchOption(BaseModel):
    id: str
    category: Literal["flight", "lodging", "activity"]
    title: str
    provider: str
    price: float = Field(ge=0)
    currency: str = "USD"
    score: int = Field(ge=0, le=100)
    details: list[str] = Field(default_factory=list)
    is_mock: bool = True


class ResearchResult(BaseModel):
    summary: str
    estimated_total: float = Field(ge=0)
    currency: str = "USD"
    budget_assessment: Literal["within_budget", "near_budget", "over_budget", "unknown"]
    flights: list[ResearchOption] = Field(default_factory=list)
    lodging: list[ResearchOption] = Field(default_factory=list)
    activities: list[ResearchOption] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    generated_at: str
    uses_mock_data: bool = True
