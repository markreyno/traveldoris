# Trip planning with Doris

Source: https://chatgpt.com/share/6a79301f-e24c-83e8-9b82-a5b91297a8e4

Saved from a public ChatGPT shared conversation.

## User

OpenAI will power travel doris. It will have to convert these prompts into a json file that can create an itinerary for trips. It can ask more questions to clarify. “I want to plan a trip in the next month to japan and visit disney land, my budget is around $3,000”
 
“I want to plan a trip in the next month to japan and visit disney land, my budget is around $1,500”
 
“I need to visit my mom in boston next week, I’m leaving out of san fran. Find a cheap flight and a rental car”
 
“I want to plan a 1 month trip to Europe. I want to see the parthenon, visit Switzerland and end the trip in turkey. How would I get around once landing there? Where should I land for the most optimal trip. Where will I stay. I want the best weather when visiting Switzerland. My budget is 2,000”
 
I want to visit California. I want to visit the major national parks there. I’m flying out of las vegas. How should I travel in the state, how much would gas and time cost driving around to locations”
 
“I want to go on a weekend trip to ocean shores wa. I’m leaving from Bellingham wa and I want to know if there is anything cool to visit on the way and how much would the hotel be”. What would the code be in python and typescript

## Assistant

For TravelDoris, I’d separate this into two stages: **OpenAI turns natural language into a strict `TripRequest` object**, then your backend uses that object to call flight/hotel/car/maps APIs and build the itinerary. The important part is that the model should **not invent prices or flights**—it should identify what it knows, what’s missing, and which tools the itinerary builder needs.

## Assistant

Yes — I’d model Doris as a **trip-requirements parser** first, not an itinerary generator. The OpenAI model’s first job is to turn messy user language into a predictable object your Python backend understands. Then FastAPI decides whether it has enough information to start calling Duffle, hotel, maps, rental-car, weather, etc. APIs.

For example, your first Japan prompt might eventually become:

```json
{
  "destination": ["Japan"],
  "origin": null,
  "date": {
    "type": "flexible",
    "start": null,
    "end": null,
    "description": "within the next month"
  },
  "duration_days": null,
  "budget": {
    "amount": 3000,
    "currency": "USD"
  },
  "travelers": 1,
  "must_visit": [
    "Tokyo Disneyland"
  ],
  "transportation": {
    "flight": true,
    "rental_car": false,
    "public_transit": null,
    "driving": null
  },
  "needs": {
    "flights": true,
    "hotels": true,
    "activities": true,
    "ground_transportation": true,
    "driving_costs": false,
    "weather_optimization": false
  },
  "missing_information": [
    "origin airport",
    "trip duration"
  ],
  "ready_to_search": false
}
```

That's much easier for the rest of Doris to work with.

The current OpenAI API centers new integrations on the **Responses API** rather than the older Assistants API. citeturn254870search1turn254870search2

## 1. Python: define the TripRequest

Since you're already using FastAPI, I'd use **Pydantic** for this.

```python
# models/trip.py

from pydantic import BaseModel, Field
from typing import Optional, Literal


class DateRequirements(BaseModel):
    type: Literal["exact", "flexible", "unknown"]

    start: Optional[str] = None
    end: Optional[str] = None

    # Keep the user's natural-language requirement too.
    # Example: "next month", "best weather in Switzerland"
    description: Optional[str] = None


class Budget(BaseModel):
    amount: Optional[float] = None
    currency: str = "USD"


class TransportationRequirements(BaseModel):
    flight: bool = False
    rental_car: bool = False

    # None means user hasn't expressed a preference.
    public_transit: Optional[bool] = None
    driving: Optional[bool] = None


class SearchNeeds(BaseModel):
    flights: bool = False
    hotels: bool = False
    rental_cars: bool = False
    activities: bool = False
    ground_transportation: bool = False
    driving_costs: bool = False
    weather_optimization: bool = False


class TripRequest(BaseModel):
    destinations: list[str] = []

    origin: Optional[str] = None

    date: DateRequirements

    duration_days: Optional[int] = None

    budget: Budget

    travelers: int = 1

    must_visit: list[str] = []
    preferences: list[str] = []

    transportation: TransportationRequirements

    needs: SearchNeeds

    missing_information: list[str] = []

    ready_to_search: bool = False
```

Notice something important here: **`TripRequest` isn't the itinerary.**

It's the specification for making the itinerary.

So your architecture becomes:

```text
User
 │
 ▼
React
 │
 │ POST /trip/message
 ▼
FastAPI
 │
 ▼
OpenAI
 │
 │ extracts requirements
 ▼
TripRequest
 │
 ├── missing info? ──► ask user question
 │
 └── enough info?
       │
       ├── Flight API
       ├── Hotel API
       ├── Rental Car API
       ├── Maps / routes
       ├── Weather
       └── Activities
                │
                ▼
         Itinerary Builder
```

That separation will make TravelDoris much easier to maintain. memcite

## 2. Add the AI result

I'd actually have OpenAI return one level above `TripRequest`.

```python
class DorisParserResult(BaseModel):
    trip: TripRequest

    status: Literal[
        "needs_clarification",
        "ready"
    ]

    clarification_question: Optional[str] = None
```

Why?

Because Doris needs to be capable of saying:

```json
{
  "status": "needs_clarification",
  "clarification_question": "What city or airport will you be flying from?",
  "trip": {
    ...
  }
}
```

instead of pretending it has everything it needs.

---

# 3. OpenAI parser

Your service could look roughly like this:

```python
# services/doris_parser.py

from openai import OpenAI

from models.trip import DorisParserResult


client = OpenAI()


SYSTEM_PROMPT = """
You are Doris, the trip requirements parser for TravelDoris.

Your job is NOT to invent flights, hotel prices, driving times,
weather, availability, or itineraries.

Your job is to convert the user's conversation into a structured
TripRequest.

Rules:

1. Extract information explicitly provided by the user.
2. You may infer obvious intent, but never invent factual travel data.
3. Record missing information that materially prevents a trip search.
4. Ask only one clarification question at a time.
5. Do not ask questions whose answers can later be determined
   through travel APIs.
6. Mark ready_to_search=true once enough information exists to
   begin researching the trip.
7. Relative dates such as "next week" or "next month" should be
   preserved in date.description.
8. Locations should be normalized when obvious.
9. must_visit contains requirements the itinerary must satisfy.
10. preferences contain softer preferences.
11. needs describes which external services TravelDoris will need.

Examples:

"I need to visit my mom in Boston next week, I'm leaving out of
San Francisco. Find a cheap flight and a rental car"

means:
- destination: Boston
- origin: San Francisco
- flexible relative dates: next week
- flight search needed
- rental car search needed
- price preference: cheap
"""


def parse_trip_request(
    conversation: str
) -> DorisParserResult:

    response = client.responses.parse(
        model="gpt-5.6",
        instructions=SYSTEM_PROMPT,
        input=conversation,
        text_format=DorisParserResult,
    )

    return response.output_parsed
```

The exact SDK surface can evolve, so I'd pin your `openai` dependency and code against the version you install rather than copying random older Assistants-API examples. OpenAI's current docs identify Responses as the current API family. citeturn254870search1

---

# 4. Connect it to FastAPI

Now you expose one endpoint to React.

```python
# main.py

from fastapi import FastAPI
from pydantic import BaseModel

from services.doris_parser import parse_trip_request


app = FastAPI()


class UserMessage(BaseModel):
    message: str


@app.post("/trip/parse")
def parse_trip(message: UserMessage):

    result = parse_trip_request(
        conversation=message.message
    )

    return result
```

So React sends:

```json
{
  "message": "I need to visit my mom in Boston next week, I'm leaving out of San Fran. Find a cheap flight and a rental car"
}
```

FastAPI passes that string to OpenAI.

OpenAI might return:

```json
{
  "trip": {
    "destinations": [
      "Boston, MA"
    ],

    "origin": "San Francisco, CA",

    "date": {
      "type": "flexible",
      "start": null,
      "end": null,
      "description": "next week"
    },

    "duration_days": null,

    "budget": {
      "amount": null,
      "currency": "USD"
    },

    "travelers": 1,

    "must_visit": [],

    "preferences": [
      "cheap flight"
    ],

    "transportation": {
      "flight": true,
      "rental_car": true,
      "public_transit": null,
      "driving": null
    },

    "needs": {
      "flights": true,
      "hotels": false,
      "rental_cars": true,
      "activities": false,
      "ground_transportation": false,
      "driving_costs": false,
      "weather_optimization": false
    },

    "missing_information": [
      "return date or trip duration"
    ],

    "ready_to_search": false
  },

  "status": "needs_clarification",

  "clarification_question":
    "How long will you be staying in Boston?"
}
```

That is exactly the behavior I think you want.

---

# 5. React + TypeScript

Your TypeScript types should mirror your Python models.

```typescript
// types/trip.ts

export interface DateRequirements {
  type: "exact" | "flexible" | "unknown";
  start: string | null;
  end: string | null;
  description: string | null;
}

export interface Budget {
  amount: number | null;
  currency: string;
}

export interface TransportationRequirements {
  flight: boolean;
  rental_car: boolean;
  public_transit: boolean | null;
  driving: boolean | null;
}

export interface SearchNeeds {
  flights: boolean;
  hotels: boolean;
  rental_cars: boolean;
  activities: boolean;
  ground_transportation: boolean;
  driving_costs: boolean;
  weather_optimization: boolean;
}

export interface TripRequest {
  destinations: string[];
  origin: string | null;

  date: DateRequirements;

  duration_days: number | null;

  budget: Budget;

  travelers: number;

  must_visit: string[];
  preferences: string[];

  transportation: TransportationRequirements;

  needs: SearchNeeds;

  missing_information: string[];

  ready_to_search: boolean;
}

export interface DorisParserResult {
  trip: TripRequest;

  status:
    | "needs_clarification"
    | "ready";

  clarification_question: string | null;
}
```

Now create the API call.

```typescript
// api/doris.ts

import type {
  DorisParserResult
} from "../types/trip";


export async function sendMessageToDoris(
  message: string
): Promise<DorisParserResult> {

  const response = await fetch(
    "http://localhost:8000/trip/parse",
    {
      method: "POST",

      headers: {
        "Content-Type": "application/json"
      },

      body: JSON.stringify({
        message
      })
    }
  );

  if (!response.ok) {
    throw new Error(
      "Failed to communicate with Doris"
    );
  }

  return response.json();
}
```

And your component:

```tsx
import { useState } from "react";

import { sendMessageToDoris } from "./api/doris";

import type {
  TripRequest
} from "./types/trip";


export default function DorisChat() {

  const [message, setMessage] =
    useState("");

  const [dorisMessage, setDorisMessage] =
    useState("");

  const [trip, setTrip] =
    useState<TripRequest | null>(null);


  async function handleSubmit() {

    const result =
      await sendMessageToDoris(message);

    setTrip(result.trip);

    if (
      result.status ===
      "needs_clarification"
    ) {

      setDorisMessage(
        result.clarification_question ??
        "I need a little more information."
      );

      return;
    }


    setDorisMessage(
      "Great. I have enough information to start planning your trip."
    );
  }


  return (
    <div>

      <h1>TravelDoris</h1>

      <textarea
        value={message}
        onChange={(event) =>
          setMessage(event.target.value)
        }
      />

      <button onClick={handleSubmit}>
        Send
      </button>

      {dorisMessage && (
        <p>{dorisMessage}</p>
      )}

    </div>
  );
}
```

There's one major thing we haven't implemented yet, though: **conversation state**.

Right now if Doris asks:

> How long will you be staying in Boston?

and the user responds:

> 4 days

sending only `"4 days"` to OpenAI loses the original context.

For Doris, we want something more like:

```text
USER:
I need to visit my mom in Boston next week.
I'm leaving out of San Francisco.
Find a cheap flight and rental car.

DORIS:
How long will you be staying in Boston?

USER:
4 days.
```

Then OpenAI updates the **existing** TripRequest instead of creating another one.

---

## Your six examples become different search plans

This is actually where your architecture gets interesting.

**Japan — $3,000**

```text
OpenAI parser
    ↓
Japan
Disneyland mandatory
budget = $3000
next month
    ↓
Needs:
flight
hotel
activities
ground transportation
```

Doris probably asks:

> What airport are you flying from, and about how many days do you want to stay?

Though I would have Doris ask these individually if you're enforcing one-question-at-a-time clarification.

The **$1,500 Japan** request creates almost exactly the same requirements object. That's good. The difference isn't parsing — it's what happens **afterward**.

```text
$3,000
    ↓
search APIs
    ↓
probably feasible

$1,500
    ↓
search APIs
    ↓
possibly infeasible
    ↓
Doris changes itinerary / duration /
accommodations or informs user
```

The LLM shouldn't decide beforehand that $1,500 is impossible.

Your travel APIs should give it evidence.

---

The **Europe prompt**:

```text
Europe
├── Parthenon
├── Switzerland
└── Turkey last

Budget: $2,000
Duration: 1 month
Weather preference: best Switzerland weather
```

turns into:

```json
{
  "destinations": [
    "Athens, Greece",
    "Switzerland",
    "Turkey"
  ],

  "duration_days": 30,

  "budget": {
    "amount": 2000,
    "currency": "USD"
  },

  "must_visit": [
    "Parthenon",
    "Switzerland",
    "Turkey"
  ],

  "preferences": [
    "Turkey must be the final destination",
    "visit Switzerland during favorable weather",
    "optimize arrival airport",
    "determine transportation between destinations"
  ],

  "needs": {
    "flights": true,
    "hotels": true,
    "rental_cars": false,
    "activities": true,
    "ground_transportation": true,
    "driving_costs": false,
    "weather_optimization": true
  }
}
```

Notice Doris hasn't decided:

```text
Athens → Zurich → Istanbul
```

yet.

That's the **planner's** job after it retrieves actual information.

---

The California national parks one is another great example:

```json
{
  "destinations": [
    "California"
  ],

  "origin": "Las Vegas, NV",

  "must_visit": [
    "major California national parks"
  ],

  "preferences": [
    "calculate driving time",
    "calculate gasoline cost",
    "determine best transportation method"
  ],

  "needs": {
    "flights": true,
    "hotels": true,
    "rental_cars": true,
    "activities": true,
    "ground_transportation": true,
    "driving_costs": true,
    "weather_optimization": false
  }
}
```

Later your route service could calculate:

```text
Las Vegas
 ↓
Death Valley
 ↓
Sequoia
 ↓
Kings Canyon
 ↓
Yosemite
 ...
```

and give Doris something like:

```json
{
  "distance_miles": 1034,
  "driving_hours": 18.4,
  "estimated_fuel_cost": 173.21
}
```

Doris then converts the raw API results into something understandable.

---

## The distinction I'd make in TravelDoris

I wouldn't call the first JSON file `Itinerary`.

I'd have **three major models**:

```text
TripRequest
     ↓
TravelResearch
     ↓
Itinerary
```

### `TripRequest`

What the person wants.

```json
{
  "destination": "...",
  "budget": 3000,
  "must_visit": [],
  "dates": {},
  "preferences": []
}
```

### `TravelResearch`

What your APIs discovered.

```json
{
  "flights": [],
  "hotels": [],
  "rental_cars": [],
  "routes": [],
  "weather": [],
  "activities": []
}
```

### `Itinerary`

What Doris finally recommends.

```json
{
  "total_cost": 2743.20,

  "days": [
    {
      "day": 1,
      "location": "Tokyo",
      "hotel": {},
      "activities": [],
      "transportation": []
    }
  ]
}
```

That gives you a very clean pipeline:

```text
             OPENAI
               │
User prompt ───►│
               ▼
          TripRequest
               │
               │
      ┌────────┼────────┐
      ▼        ▼        ▼
   Flights   Hotels    Maps
      │        │        │
      └────────┼────────┘
               ▼
        TravelResearch
               │
               ▼
             Doris
               │
               ▼
          Itinerary #1
          Itinerary #2
          Itinerary #3
```

That also fits your earlier decision that **Doris is the one manager for the MVP**, instead of creating separate flight/hotel/activity AI agents. memcite

The next piece I'd build is the **multi-turn `TripRequest` updater**. That's where the project starts to feel like an actual travel agent: the user gives the Japan request → Doris detects missing origin/duration → asks a question → user answers → the same JSON object gets updated → once `ready_to_search == true`, FastAPI starts calling your travel APIs.
