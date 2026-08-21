from fastapi.testclient import TestClient

from backend.main import app
from backend.manager.readiness import evaluate_trip
from backend.models.trip import DateRequirements, TripRequest


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_trip_contract(monkeypatch) -> None:
    expected = evaluate_trip(
        TripRequest(
            destinations=["Boston, MA"],
            origin="San Francisco, CA",
            date=DateRequirements(type="flexible", description="next week"),
        )
    )
    monkeypatch.setattr("backend.main.parse_trip_request", lambda *_: expected)
    response = client.post(
        "/trip/parse",
        json={"messages": [{"role": "user", "content": "I need to visit Boston next week from San Francisco."}]},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["trip"]["destinations"] == ["Boston, MA"]
    assert payload["status"] == "collecting_basics"
    assert payload["next_questions"]
    assert payload["completion_percentage"] < 100
