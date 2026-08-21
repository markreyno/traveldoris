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
from backend.scripts import test_doris_chat as cli
from backend.scripts.test_doris_chat import is_ready_status, prompt_yes_no


def test_cli_recognizes_current_ready_statuses() -> None:
    assert is_ready_status("ready_for_research") is True
    assert is_ready_status("ready_for_itinerary") is True
    assert is_ready_status("collecting_basics") is False
    assert is_ready_status("ready") is False


def ready_result(*, deferred: bool = False):
    return evaluate_trip(
        TripRequest(
            trip_type="international",
            destinations=["Tokyo, Japan"],
            origin="Seattle, WA",
            date=DateRequirements(type="flexible", description="next month"),
            duration_days=7,
            budget=Budget() if deferred else Budget(amount=3000, scope="total"),
            travelers=TravelerRequirements(adults=2, children=0),
            must_visit=["Tokyo Disneyland"],
            preferences=["food"],
            transportation=TransportationRequirements(flight=True, driving=False),
            lodging=LodgingRequirements(needed=True, rooms=1, type="hotel"),
            field_resolutions=(
                [FieldResolution(field="budget.amount", status="user_unsure")]
                if deferred
                else []
            ),
        )
    )


def test_yes_no_prompt_defaults_to_no(monkeypatch) -> None:
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert prompt_yes_no("Continue?") is False


def test_cli_prints_mock_research_after_confirmation(monkeypatch, capsys) -> None:
    answers = iter(["Plan Japan", "yes"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(cli, "parse_trip_request", lambda *_: ready_result())
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "Mock research results" in output
    assert "Mock Air" in output
    assert "Mock Stays" in output
    assert "Mock Experiences" in output


def test_cli_requires_deferred_assumption_acceptance(monkeypatch, capsys) -> None:
    answers = iter(["Plan Japan", "yes", "no"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr(cli, "parse_trip_request", lambda *_: ready_result(deferred=True))
    assert cli.main() == 0
    output = capsys.readouterr().out
    assert "deferred assumptions were not accepted" in output
    assert "Mock research results" not in output
