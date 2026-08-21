from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


TripType = Literal["unknown", "flight_trip", "road_trip", "local_trip", "multi_city", "international", "family_visit", "business", "open_ended"]
PlanningStatus = Literal["collecting_basics", "collecting_logistics", "collecting_preferences", "ready_for_research", "ready_for_itinerary"]
FieldResolutionStatus = Literal[
    "provided",
    "user_unsure",
    "declined",
    "not_applicable",
    "use_recommended_default",
]


class DateRequirements(BaseModel):
    type: Literal["exact", "flexible", "unknown"] = "unknown"
    start: Optional[str] = None
    end: Optional[str] = None
    description: Optional[str] = None


class Budget(BaseModel):
    amount: Optional[float] = Field(default=None, ge=0)
    currency: str = "USD"
    scope: Optional[Literal["total", "per_person", "on_ground"]] = None
    flexible: Optional[bool] = None
    includes: list[str] = Field(default_factory=list)


class TravelerRequirements(BaseModel):
    adults: Optional[int] = Field(default=None, ge=1)
    children: Optional[int] = Field(default=None, ge=0)
    child_ages: list[int] = Field(default_factory=list)


class TransportationRequirements(BaseModel):
    flight: Optional[bool] = None
    rental_car: Optional[bool] = None
    public_transit: Optional[bool] = None
    driving: Optional[bool] = None


class LodgingRequirements(BaseModel):
    needed: Optional[bool] = None
    type: Optional[Literal["hotel", "hostel", "vacation_rental", "resort", "other"]] = None
    rooms: Optional[int] = Field(default=None, ge=1)


class TripConstraints(BaseModel):
    accessibility: list[str] = Field(default_factory=list)
    dietary: list[str] = Field(default_factory=list)
    mobility: list[str] = Field(default_factory=list)
    max_driving_hours_per_day: Optional[float] = Field(default=None, gt=0, le=24)
    notes: list[str] = Field(default_factory=list)


class SearchNeeds(BaseModel):
    flights: Optional[bool] = None
    hotels: Optional[bool] = None
    rental_cars: Optional[bool] = None
    activities: Optional[bool] = None
    ground_transportation: Optional[bool] = None
    driving_costs: Optional[bool] = None
    weather_optimization: Optional[bool] = None


class FieldResolution(BaseModel):
    field: str
    status: FieldResolutionStatus
    note: Optional[str] = None


class TripRequest(BaseModel):
    trip_type: TripType = "unknown"
    destinations: list[str] = Field(default_factory=list)
    origin: Optional[str] = None
    date: DateRequirements = Field(default_factory=DateRequirements)
    duration_days: Optional[int] = Field(default=None, ge=1)
    budget: Budget = Field(default_factory=Budget)
    travelers: TravelerRequirements = Field(default_factory=TravelerRequirements)
    must_visit: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    pace: Optional[Literal["relaxed", "balanced", "busy"]] = None
    transportation: TransportationRequirements = Field(default_factory=TransportationRequirements)
    lodging: LodgingRequirements = Field(default_factory=LodgingRequirements)
    constraints: TripConstraints = Field(default_factory=TripConstraints)
    needs: SearchNeeds = Field(default_factory=SearchNeeds)
    field_resolutions: list[FieldResolution] = Field(default_factory=list)
    planning_status: PlanningStatus = "collecting_basics"
    ready_to_search: bool = False


class MissingField(BaseModel):
    field: str
    section: Literal["basics", "logistics", "preferences"]
    priority: Literal["required", "recommended"]
    reason: str


class DorisExtractionResult(BaseModel):
    trip: TripRequest


class DorisParserResult(BaseModel):
    trip: TripRequest
    status: PlanningStatus
    clarification_question: Optional[str] = None
    next_questions: list[str] = Field(default_factory=list)
    missing_fields: list[MissingField] = Field(default_factory=list)
    deferred_fields: list[str] = Field(default_factory=list)
    completion_percentage: int = Field(ge=0, le=100)


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=10_000)


class ParseTripRequest(BaseModel):
    messages: list[ConversationMessage] = Field(min_length=1, max_length=30)
    current_trip: Optional[TripRequest] = None
