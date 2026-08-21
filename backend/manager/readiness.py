from __future__ import annotations

from typing import Literal

from backend.models.trip import DorisParserResult, MissingField, TripRequest


QUESTION_TEXT = {
    "destinations": "Where would you like to go?",
    "date": "What travel dates or date range work for you?",
    "duration_days": "About how many days would you like the trip to be?",
    "origin": "What city or airport will you leave from?",
    "travelers.adults": "How many adults are traveling?",
    "budget.amount": "What total budget should I plan around, or should I keep it flexible?",
    "budget.scope": "Is that budget total, per person, or only for expenses after arrival?",
    "transportation": "Should I plan for flights, driving, or public transportation?",
    "lodging.needed": "Will you need lodging included in the plan?",
    "lodging.rooms": "How many rooms will you need?",
    "preferences": "What pace, interests, or accommodation style would make this trip feel right?",
}

DEFERRED_STATUSES = {
    "user_unsure",
    "declined",
    "not_applicable",
    "use_recommended_default",
}


def _issue(field: str, section: Literal["basics", "logistics", "preferences"], priority: Literal["required", "recommended"], reason: str) -> MissingField:
    return MissingField(field=field, section=section, priority=priority, reason=reason)


def _has_date(trip: TripRequest) -> bool:
    return bool(trip.date.start or trip.date.end or trip.date.description)


def _has_transport_choice(trip: TripRequest) -> bool:
    transport = trip.transportation
    return any(value is not None for value in (transport.flight, transport.driving, transport.public_transit))


def _is_deferred(trip: TripRequest, field: str) -> bool:
    resolution = next((item for item in trip.field_resolutions if item.field == field), None)
    return resolution is not None and resolution.status in DEFERRED_STATUSES


def find_missing_fields(trip: TripRequest) -> list[MissingField]:
    missing: list[MissingField] = []
    if not trip.destinations and not _is_deferred(trip, "destinations"):
        missing.append(_issue("destinations", "basics", "required", "A destination anchors every trip search."))
    if not _has_date(trip) and not _is_deferred(trip, "date"):
        missing.append(_issue("date", "basics", "required", "Travel dates or a flexible window are required for availability."))
    if trip.duration_days is None and not (trip.date.start and trip.date.end) and not _is_deferred(trip, "duration_days"):
        missing.append(_issue("duration_days", "basics", "required", "Trip length is required to plan lodging and an itinerary."))
    if not trip.origin and trip.trip_type != "local_trip" and not _is_deferred(trip, "origin"):
        missing.append(_issue("origin", "basics", "required", "The starting point is required to plan transportation."))
    if trip.travelers.adults is None and not _is_deferred(trip, "travelers.adults"):
        missing.append(_issue("travelers.adults", "basics", "required", "Traveler count affects flight, room, and activity searches."))
    if trip.budget.amount is None and trip.budget.flexible is not True and not _is_deferred(trip, "budget.amount"):
        missing.append(_issue("budget.amount", "logistics", "required", "A budget or explicit flexible-budget choice is needed to rank options."))
    elif trip.budget.amount is not None and trip.budget.scope is None and not _is_deferred(trip, "budget.scope"):
        missing.append(_issue("budget.scope", "logistics", "required", "The budget scope prevents misleading recommendations."))
    if not _has_transport_choice(trip) and trip.trip_type != "local_trip" and not _is_deferred(trip, "transportation"):
        missing.append(_issue("transportation", "logistics", "required", "Doris must know which major transportation modes to research."))
    if trip.lodging.needed is None and not _is_deferred(trip, "lodging.needed"):
        missing.append(_issue("lodging.needed", "logistics", "required", "Lodging must be explicitly included or excluded."))
    elif trip.lodging.needed and trip.lodging.rooms is None and not _is_deferred(trip, "lodging.rooms"):
        missing.append(_issue("lodging.rooms", "logistics", "required", "Room count is required for lodging searches."))
    if not trip.preferences and not trip.must_visit and trip.pace is None and not _is_deferred(trip, "preferences"):
        missing.append(_issue("preferences", "preferences", "recommended", "Preferences make the itinerary useful rather than generic."))
    return missing


def _questions_for(missing: list[MissingField]) -> list[str]:
    required = [item for item in missing if item.priority == "required"]
    source = required or missing
    if not source:
        return []
    section = source[0].section
    return [QUESTION_TEXT[item.field] for item in source if item.section == section][:3]


def _status_for(missing: list[MissingField], trip: TripRequest) -> str:
    required = [item for item in missing if item.priority == "required"]
    if any(item.section == "basics" for item in required):
        return "collecting_basics"
    if any(item.section == "logistics" for item in required):
        return "collecting_logistics"
    if required:
        return "collecting_preferences"
    if not missing and trip.preferences:
        return "ready_for_itinerary"
    return "ready_for_research"


def evaluate_trip(trip: TripRequest) -> DorisParserResult:
    missing = find_missing_fields(trip)
    questions = _questions_for(missing)
    required_count = sum(item.priority == "required" for item in missing)
    completion = max(0, min(100, round((10 - required_count) / 10 * 100)))
    status = _status_for(missing, trip)
    trip.planning_status = status
    trip.ready_to_search = required_count == 0
    deferred_fields = sorted(
        field
        for resolution in trip.field_resolutions
        if resolution.status in DEFERRED_STATUSES
        for field in [resolution.field]
    )
    return DorisParserResult(
        trip=trip,
        status=status,
        clarification_question=" ".join(questions) if questions else None,
        next_questions=questions,
        missing_fields=missing,
        deferred_fields=deferred_fields,
        completion_percentage=completion,
    )
