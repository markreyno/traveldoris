from fastapi.testclient import TestClient

import backend.main as main_module
from backend.manager.readiness import evaluate_trip
from backend.models.trip import (
    Budget,
    DateRequirements,
    FieldResolution,
    LodgingRequirements,
    TransportationRequirements,
    TravelerRequirements,
    TripRequest,
)
from backend.storage.trip_store import TripSessionStore


client = TestClient(main_module.app)


def ready_trip(*, deferred: bool = False) -> TripRequest:
    resolutions = (
        [FieldResolution(field="budget.amount", status="user_unsure")]
        if deferred
        else []
    )
    budget = Budget() if deferred else Budget(amount=3000, scope="total")
    return TripRequest(
        trip_type="international",
        destinations=["Tokyo, Japan"],
        origin="Seattle, WA",
        date=DateRequirements(type="flexible", description="next month"),
        duration_days=7,
        budget=budget,
        travelers=TravelerRequirements(adults=2, children=0),
        must_visit=["Tokyo Disneyland"],
        preferences=["food"],
        transportation=TransportationRequirements(
            flight=True, driving=False, public_transit=True
        ),
        lodging=LodgingRequirements(needed=True, rooms=1, type="hotel"),
        field_resolutions=resolutions,
    )


def use_temp_store(monkeypatch, tmp_path) -> TripSessionStore:
    store = TripSessionStore(tmp_path / "trips.db")
    monkeypatch.setattr(main_module, "trip_store", store)
    return store


def test_session_messages_are_persisted(monkeypatch, tmp_path) -> None:
    store = use_temp_store(monkeypatch, tmp_path)
    monkeypatch.setattr(
        main_module, "parse_trip_request", lambda *_: evaluate_trip(ready_trip())
    )
    created = client.post("/trips", json={})
    assert created.status_code == 201
    session_id = created.json()["id"]

    updated = client.post(
        f"/trips/{session_id}/messages",
        json={"message": "Plan Japan next month."},
    )
    assert updated.status_code == 200
    assert len(updated.json()["messages"]) == 2
    assert updated.json()["trip"]["ready_to_search"] is True

    reopened_store = TripSessionStore(store.database_path)
    reopened = reopened_store.get(session_id)
    assert reopened is not None
    assert reopened.messages[0].content == "Plan Japan next month."


def test_research_requires_ready_trip(monkeypatch, tmp_path) -> None:
    use_temp_store(monkeypatch, tmp_path)
    session_id = client.post("/trips", json={}).json()["id"]
    response = client.post(
        f"/trips/{session_id}/research",
        json={"confirmed": True, "accept_deferred_fields": False},
    )
    assert response.status_code == 409


def test_research_requires_deferred_assumption_acceptance(monkeypatch, tmp_path) -> None:
    use_temp_store(monkeypatch, tmp_path)
    monkeypatch.setattr(
        main_module,
        "parse_trip_request",
        lambda *_: evaluate_trip(ready_trip(deferred=True)),
    )
    session_id = client.post("/trips", json={}).json()["id"]
    client.post(f"/trips/{session_id}/messages", json={"message": "You choose my budget."})

    rejected = client.post(
        f"/trips/{session_id}/research",
        json={"confirmed": True, "accept_deferred_fields": False},
    )
    assert rejected.status_code == 409

    accepted = client.post(
        f"/trips/{session_id}/research",
        json={"confirmed": True, "accept_deferred_fields": True},
    )
    assert accepted.status_code == 200
    payload = accepted.json()
    assert payload["research_confirmed"] is True
    assert payload["research"]["uses_mock_data"] is True
    assert payload["research"]["flights"]
    assert payload["research"]["lodging"]
    assert payload["research"]["activities"]


def test_research_results_are_ranked(monkeypatch, tmp_path) -> None:
    use_temp_store(monkeypatch, tmp_path)
    monkeypatch.setattr(
        main_module, "parse_trip_request", lambda *_: evaluate_trip(ready_trip())
    )
    session_id = client.post("/trips", json={}).json()["id"]
    client.post(f"/trips/{session_id}/messages", json={"message": "Plan Japan."})
    payload = client.post(
        f"/trips/{session_id}/research",
        json={"confirmed": True, "accept_deferred_fields": False},
    ).json()["research"]
    assert payload["flights"][0]["score"] >= payload["flights"][1]["score"]
    assert payload["lodging"][0]["score"] >= payload["lodging"][1]["score"]
