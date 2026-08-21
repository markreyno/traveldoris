# TravelDoris

TravelDoris is an AI trip-intake assistant. This first vertical slice turns a natural-language travel request into a validated `TripRequest`, asks one clarification question at a time, and shows the evolving trip brief in a React UI.

OpenAI extracts facts and merges conversation state, while deterministic backend rules decide whether the request has enough basics, logistics, and preferences for research. Unknown choices remain `null` until the traveler explicitly confirms or declines them. Doris asks up to three related questions per turn and reports intake completion in the trip brief.

If a traveler says they are unsure, declines to answer, marks a field inapplicable, or asks Doris to recommend a default, the parser records a field resolution instead of repeatedly asking the same question. These deferred choices remain visible in the trip brief and can be confirmed later before a provider requires them.

## Run locally

1. Create and activate a Python virtual environment.
2. Install the backend: `pip install -r requirements.txt`
3. Set `OPENAI_API_KEY` in your environment. Optionally set `OPENAI_MODEL` (defaults to `gpt-5.6-terra`).
4. Start the API from the repository root: `uvicorn backend.main:app --reload`
5. In another terminal, run `cd frontend`, `npm install`, then `npm run dev`.

The Vite dev server proxies `/api` requests to FastAPI at `127.0.0.1:8000`.

## Trip workflow

Trip conversations are stored in SQLite at `backend/data/traveldoris.db` by default. Set `TRAVELDORIS_DB_PATH` to use another location.

```text
POST /trips                         Create a persistent trip session
POST /trips/{id}/messages           Add a traveler message and update intake
GET  /trips/{id}                    Restore the session
POST /trips/{id}/research           Confirm the brief and run mock research
```

Research cannot start until required intake fields are resolved. If Doris is carrying flexible or deferred assumptions, the traveler must explicitly accept them in the research request. The current flight, lodging, and activity providers are deterministic mocks; every option is marked `is_mock: true` and no external booking action occurs.

## Verify

- Backend: `pytest backend/tests`
- Frontend: `cd frontend && npm run build`

To exercise the complete intake and mock-research flow in a terminal, run `python -m backend.scripts.test_doris_chat`. Once the brief is ready, the CLI asks for research confirmation, separately requests acceptance of any deferred assumptions, and prints the mock provider results as JSON.

The parser deliberately does not invent travel prices, schedules, weather, or availability. Provider integrations and itinerary generation are later phases.
