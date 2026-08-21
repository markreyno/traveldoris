from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.models.session import AddTripMessageRequest, CreateTripSessionRequest, StartResearchRequest, TripSession
from backend.models.trip import ConversationMessage, ParseTripRequest, DorisParserResult
from backend.services.mock_research import research_trip
from backend.services.doris_parser import DorisConfigurationError, parse_trip_request
from backend.storage.trip_store import TripSessionStore


app = FastAPI(title="TravelDoris API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
trip_store = TripSessionStore()


def _get_session(session_id: str) -> TripSession:
    session = trip_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Trip session not found.")
    return session


def _doris_reply(result: DorisParserResult) -> str:
    if result.status in {"ready_for_research", "ready_for_itinerary"}:
        if result.deferred_fields:
            return "I have enough to research your trip. Review the flexible assumptions, then confirm when you are ready."
        return "I have enough information to research your trip. Review the brief and confirm when you are ready."
    return result.clarification_question or "Tell me anything else that matters for this trip."


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/trip/parse", response_model=DorisParserResult)
def parse_trip(payload: ParseTripRequest) -> DorisParserResult:
    try:
        return parse_trip_request(payload.messages, payload.current_trip)
    except DorisConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Doris could not parse the trip request. Please try again.",
        ) from exc


@app.post("/trips", response_model=TripSession, status_code=201)
def create_trip_session(_: CreateTripSessionRequest) -> TripSession:
    return trip_store.create()


@app.get("/trips/{session_id}", response_model=TripSession)
def get_trip_session(session_id: str) -> TripSession:
    return _get_session(session_id)


@app.post("/trips/{session_id}/messages", response_model=TripSession)
def add_trip_message(session_id: str, payload: AddTripMessageRequest) -> TripSession:
    session = _get_session(session_id)
    session.messages.append(ConversationMessage(role="user", content=payload.message))
    try:
        result = parse_trip_request(session.messages, session.trip)
    except DorisConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Doris could not update this trip. Please try again.") from exc
    session.trip = result.trip
    session.intake = result
    session.messages.append(ConversationMessage(role="assistant", content=_doris_reply(result)))
    session.research_confirmed = False
    session.deferred_fields_accepted = False
    session.research = None
    return trip_store.save(session)


@app.post("/trips/{session_id}/research", response_model=TripSession)
def start_trip_research(session_id: str, payload: StartResearchRequest) -> TripSession:
    session = _get_session(session_id)
    if session.trip is None or session.intake is None or not session.trip.ready_to_search:
        raise HTTPException(status_code=409, detail="Complete the required trip details before research.")
    if not payload.confirmed:
        raise HTTPException(status_code=409, detail="Confirm the trip brief before research.")
    if session.intake.deferred_fields and not payload.accept_deferred_fields:
        raise HTTPException(status_code=409, detail="Accept the deferred assumptions before research.")
    session.research_confirmed = True
    session.deferred_fields_accepted = payload.accept_deferred_fields
    session.research = research_trip(session.trip)
    return trip_store.save(session)
