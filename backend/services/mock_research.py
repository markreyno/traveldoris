from __future__ import annotations

from datetime import datetime, timezone

from backend.models.research import ResearchOption, ResearchResult
from backend.models.trip import TripRequest


def _flight_options(trip: TripRequest) -> list[ResearchOption]:
    wants_flight = trip.transportation.flight is True or trip.trip_type in {
        "flight_trip", "international", "multi_city", "family_visit", "business"
    }
    if not wants_flight:
        return []
    destination = trip.destinations[0] if trip.destinations else "your destination"
    adults = trip.travelers.adults or 1
    base = 420 * adults
    return [
        ResearchOption(id="mock-flight-value", category="flight", title=f"Best-value route to {destination}", provider="Mock Air", price=base, score=92, details=["1 stop or fewer", "Standard economy", "Flexible-date estimate"]),
        ResearchOption(id="mock-flight-fast", category="flight", title=f"Fastest route to {destination}", provider="Mock Air", price=round(base * 1.28, 2), score=86, details=["Shortest estimated travel time", "Standard economy", "Flexible-date estimate"]),
    ]


def _lodging_options(trip: TripRequest) -> list[ResearchOption]:
    if trip.lodging.needed is False:
        return []
    destination = trip.destinations[0] if trip.destinations else "Destination"
    nights = max(1, (trip.duration_days or 5) - 1)
    rooms = trip.lodging.rooms or 1
    base = 135 * nights * rooms
    return [
        ResearchOption(id="mock-stay-central", category="lodging", title=f"Central stay in {destination}", provider="Mock Stays", price=base, score=90, details=[f"{nights} nights", f"{rooms} room(s)", "Central location"]),
        ResearchOption(id="mock-stay-budget", category="lodging", title=f"Budget-friendly stay in {destination}", provider="Mock Stays", price=round(base * 0.78, 2), score=84, details=[f"{nights} nights", f"{rooms} room(s)", "Transit accessible"]),
    ]


def _activity_options(trip: TripRequest) -> list[ResearchOption]:
    destination = trip.destinations[0] if trip.destinations else "the destination"
    requested = trip.must_visit[:2] or [f"Highlights of {destination}", "Local food and culture"]
    return [
        ResearchOption(id=f"mock-activity-{index}", category="activity", title=title, provider="Mock Experiences", price=65 + index * 30, score=94 - index * 4, details=["Traveler-interest match", "Estimated per-person price"])
        for index, title in enumerate(requested)
    ]


def research_trip(trip: TripRequest) -> ResearchResult:
    flights = _flight_options(trip)
    lodging = _lodging_options(trip)
    activities = _activity_options(trip)
    selected = [options[0] for options in (flights, lodging, activities) if options]
    estimated_total = round(sum(option.price for option in selected), 2)
    budget = trip.budget.amount
    if budget is None:
        assessment = "unknown"
    elif estimated_total <= budget * 0.9:
        assessment = "within_budget"
    elif estimated_total <= budget * 1.1:
        assessment = "near_budget"
    else:
        assessment = "over_budget"
    assumptions = [
        f"{resolution.field}: {resolution.status.replace('_', ' ')}"
        for resolution in trip.field_resolutions
        if resolution.status != "provided"
    ]
    return ResearchResult(
        summary=f"Mock research produced {len(selected)} recommended components for {', '.join(trip.destinations) or 'this trip'}.",
        estimated_total=estimated_total,
        currency=trip.budget.currency,
        budget_assessment=assessment,
        flights=sorted(flights, key=lambda option: option.score, reverse=True),
        lodging=sorted(lodging, key=lambda option: option.score, reverse=True),
        activities=sorted(activities, key=lambda option: option.score, reverse=True),
        assumptions=assumptions,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
