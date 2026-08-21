# TravelDoris MVP

## Vision

TravelDoris is an AI travel agent that helps users plan complete trips by reasoning about their goals, gathering live travel information, ranking options, and eventually booking travel.

Unlike a traditional chatbot, Doris acts as a travel planner that coordinates multiple services and presents the best itinerary.

---

# MVP Goal

Build an AI-powered travel planner that can:

- Understand natural language trip requests
- Ask follow-up questions when information is missing
- Search flights
- Search hotels
- Recommend activities
- Generate a complete itinerary

---

# High-Level Architecture

```text
                 User
                  |
                  v
        React + TypeScript Frontend
                  |
                  v
          FastAPI Backend Server
                  |
                  v
        -------------------------
        | Doris Trip Manager    |
        -------------------------
                  |
     --------------------------------
     |              |               |
 Flight Service  Hotel Service  Activity Service
     |              |               |
 Duffel Flights  Duffel Stays  Viator API
```

---

# Technology Stack

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS

Responsibilities:

- Chat interface
- Itinerary display
- Cards for flights/hotels/activities

---

## Backend

- Python
- FastAPI
- Pydantic

Responsibilities:

- API endpoints
- AI orchestration
- External API integration

---

## AI Layer

Initial version:

- OpenAI API

Future:

- Local models via Ollama

---

# Project Structure

```text
traveldoris/

├── frontend/
│
├── backend/
│   ├── main.py
│   ├── manager/
│   │   └── doris.py
│   │
│   ├── models/
│   │   └── trip.py
│   │
│   ├── services/
│   │   ├── flight_service.py
│   │   ├── hotel_service.py
│   │   ├── activity_service.py
│   │
│   └── prompts/
│
└── README.md
```

---

# MVP Agent Strategy

TravelDoris will not use separate flight, hotel, or activity agents in the first version.

The Doris trip manager will:

1. Understand the user's travel request.
2. Identify missing information.
3. Call flight, hotel, and activity services.
4. Combine and rank the returned options.
5. Generate the itinerary.
6. Perform a basic quality check on the final result.

The external integrations are deterministic services, not independent AI agents.

```text
User Request
     |
     v
Doris Trip Manager
     |
     +-- Flight Service
     +-- Hotel Service
     +-- Activity Service
     |
     v
Ranked Trip Plan
```

---

# MVP Travel Data Providers

| Category | Provider | Purpose |
| --- | --- | --- |
| Flights | Duffel Flights | Search flight offers and provide a future path toward booking |
| Hotels | Duffel Stays | Search accommodation options and provide a future path toward booking |
| Activities | Viator | Search tours, attractions, and bookable experiences |

Amadeus is no longer part of the planned MVP because its current developer-access model is not a good fit for TravelDoris's self-service development workflow.

Provider-specific code stays behind TravelDoris's service layer:

```text
Doris Trip Manager
        |
        +-- Flight Service ----> Duffel Flights
        +-- Hotel Service -----> Duffel Stays
        +-- Activity Service --> Viator
```

Doris should not contain Duffel- or Viator-specific API logic. If a provider changes later, we should be able to replace the service implementation without redesigning the trip manager.

---

# Core Data Model

The first model is a TripRequirement object.

Example:

```json
{
  "destination": "Tokyo",
  "country": "Japan",
  "duration_days": 7,
  "budget": 2000,
  "interests": ["anime", "food"],
  "missing_information": ["flight origin"]
}
```

This object becomes the shared state used by the Doris trip manager and its service integrations.

---

# Development Roadmap

## Phase 1 — Foundation

- Create React frontend
- Create FastAPI backend
- Define TripRequirement model
- Build the Doris trip manager

## Phase 2 — Flight Search

- Integrate Duffel Flights API
- Return ranked flight options

## Phase 3 — Hotel Search

- Integrate Duffel Stays API
- Rank hotels based on user preferences

## Phase 4 — Activities

- Integrate Viator for tours and activities
- Recommend attractions based on interests, budget, and itinerary fit
- Add restaurant suggestions

## Phase 5 — Itinerary

Generate a day-by-day travel plan using the collected information.

## Future Features

- Flight booking
- Hotel booking
- Social media discovery
- Maps
- Price monitoring
- User memory/preferences
- Optional multi-agent architecture
- Advanced independent quality-checking agent

---

# Design Philosophy

Doris should behave like a professional travel advisor:

1. Understand the user's intent.
2. Ask clarifying questions.
3. Gather reliable data.
4. Compare options.
5. Explain recommendations.
6. Produce a polished itinerary.

For the MVP, Doris is the only AI decision-maker. Flight, hotel, and activity components are regular services or tools that return data to Doris.

This keeps the first version simpler, cheaper, easier to debug, and realistic to complete within one month. Separate agents can be introduced later only if the system becomes complex enough to benefit from them.

The system should remain modular so services—and eventually specialized agents—can be added without redesigning the entire application.
