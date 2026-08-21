import pytest

from backend.manager.readiness import evaluate_trip, find_missing_fields
from backend.models.trip import (
    Budget,
    DateRequirements,
    FieldResolution,
    LodgingRequirements,
    TransportationRequirements,
    TravelerRequirements,
    TripRequest,
)


def complete_trip(**overrides) -> TripRequest:
    values = {
        "trip_type": "international",
        "destinations": ["Tokyo, Japan"],
        "origin": "Seattle, WA",
        "date": DateRequirements(type="flexible", description="next month"),
        "duration_days": 7,
        "budget": Budget(amount=3000, scope="total", currency="USD"),
        "travelers": TravelerRequirements(adults=2, children=0),
        "transportation": TransportationRequirements(flight=True, driving=False, public_transit=True),
        "lodging": LodgingRequirements(needed=True, rooms=1, type="hotel"),
        "must_visit": ["Tokyo Disneyland"],
        "preferences": ["food", "culture"],
    }
    values.update(overrides)
    return TripRequest(**values)


def test_unknown_choices_remain_unknown_not_false() -> None:
    trip = TripRequest()
    assert trip.transportation.flight is None
    assert trip.transportation.driving is None
    assert trip.lodging.needed is None
    assert trip.needs.flights is None


def test_complete_trip_is_ready_for_itinerary() -> None:
    result = evaluate_trip(complete_trip())
    assert result.status == "ready_for_itinerary"
    assert result.trip.ready_to_search is True
    assert result.completion_percentage == 100
    assert result.next_questions == []


def test_questions_are_grouped_and_limited_to_three() -> None:
    result = evaluate_trip(TripRequest(destinations=["Japan"]))
    assert result.status == "collecting_basics"
    assert 1 <= len(result.next_questions) <= 3
    assert all(item.section == "basics" for item in result.missing_fields[:4])


def test_japan_request_with_date_asks_for_other_trip_basics() -> None:
    result = evaluate_trip(
        TripRequest(
            trip_type="international",
            destinations=["Japan"],
            date=DateRequirements(type="flexible", description="next month"),
            budget=Budget(amount=3000),
            must_visit=["Tokyo Disneyland"],
        )
    )
    assert result.next_questions == [
        "About how many days would you like the trip to be?",
        "What city or airport will you leave from?",
        "How many adults are traveling?",
    ]
    assert not any("date" in question.lower() for question in result.next_questions)


def test_budget_scope_is_required_when_amount_is_known() -> None:
    trip = complete_trip(budget=Budget(amount=1500, currency="USD"))
    fields = {item.field for item in find_missing_fields(trip)}
    assert "budget.scope" in fields
    assert evaluate_trip(trip).status == "collecting_logistics"


def test_flexible_budget_is_valid_without_amount() -> None:
    result = evaluate_trip(complete_trip(budget=Budget(flexible=True)))
    assert "budget.amount" not in {item.field for item in result.missing_fields}
    assert result.trip.ready_to_search is True


@pytest.mark.parametrize(
    "status",
    ["user_unsure", "declined", "not_applicable", "use_recommended_default"],
)
def test_resolved_without_value_is_not_asked_again(status: str) -> None:
    trip = complete_trip(
        duration_days=None,
        field_resolutions=[FieldResolution(field="duration_days", status=status)],
    )
    result = evaluate_trip(trip)
    assert "duration_days" not in {item.field for item in result.missing_fields}
    assert "duration_days" not in " ".join(result.next_questions).lower()
    assert result.deferred_fields == ["duration_days"]
    assert result.trip.ready_to_search is True


def test_explicit_no_lodging_and_no_flight_are_answers() -> None:
    trip = complete_trip(
        lodging=LodgingRequirements(needed=False),
        transportation=TransportationRequirements(
            flight=False,
            driving=True,
            public_transit=None,
            rental_car=False,
        ),
    )
    fields = {item.field for item in evaluate_trip(trip).missing_fields}
    assert "lodging.needed" not in fields
    assert "lodging.rooms" not in fields
    assert "transportation" not in fields


def test_unsure_budget_does_not_loop() -> None:
    trip = complete_trip(
        budget=Budget(),
        field_resolutions=[
            FieldResolution(field="budget.amount", status="user_unsure", note="User does not know their budget yet")
        ],
    )
    result = evaluate_trip(trip)
    assert "budget.amount" not in {item.field for item in result.missing_fields}
    assert "budget.amount" in result.deferred_fields


@pytest.mark.parametrize(
    ("trip", "expected_fields"),
    [
        (
            TripRequest(
                trip_type="international",
                destinations=["Japan"],
                date=DateRequirements(type="flexible", description="next month"),
                budget=Budget(amount=3000),
                must_visit=["Tokyo Disneyland"],
            ),
            {"duration_days", "origin", "travelers.adults", "budget.scope", "transportation", "lodging.needed"},
        ),
        (
            TripRequest(
                trip_type="family_visit",
                destinations=["Boston, MA"],
                origin="San Francisco, CA",
                date=DateRequirements(type="flexible", description="next week"),
                transportation=TransportationRequirements(flight=True, rental_car=True),
            ),
            {"duration_days", "travelers.adults", "budget.amount", "lodging.needed"},
        ),
        (
            TripRequest(
                trip_type="multi_city",
                destinations=["Athens", "Switzerland", "Turkey"],
                duration_days=30,
                budget=Budget(amount=2000),
                preferences=["best weather in Switzerland"],
            ),
            {"date", "origin", "travelers.adults", "budget.scope", "transportation", "lodging.needed"},
        ),
        (
            TripRequest(
                trip_type="road_trip",
                destinations=["California national parks"],
                origin="Las Vegas, NV",
                transportation=TransportationRequirements(driving=True),
                needs={"driving_costs": True},
            ),
            {"date", "duration_days", "travelers.adults", "budget.amount", "lodging.needed"},
        ),
        (
            TripRequest(
                trip_type="road_trip",
                destinations=["Ocean Shores, WA"],
                origin="Bellingham, WA",
                duration_days=2,
                transportation=TransportationRequirements(driving=True),
                lodging=LodgingRequirements(needed=True),
            ),
            {"date", "travelers.adults", "budget.amount", "lodging.rooms"},
        ),
    ],
)
def test_example_trips_surface_material_missing_information(trip: TripRequest, expected_fields: set[str]) -> None:
    fields = {item.field for item in find_missing_fields(trip)}
    assert expected_fields <= fields
