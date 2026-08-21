from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Optional

from openai import OpenAI

from backend.manager.readiness import evaluate_trip
from backend.models.trip import ConversationMessage, DorisExtractionResult, DorisParserResult, TripRequest


class DorisConfigurationError(RuntimeError):
    pass


SYSTEM_PROMPT = """
You are Doris, the trip-requirements parser for TravelDoris.

Convert the conversation into the supplied structured schema. Your only job is
extraction and merging. Backend code—not you—decides readiness and questions.

Do not invent flights, prices, availability, driving times, weather, an itinerary, or
user preferences. Extract explicit facts and only obvious intent. Use null for every
unknown Boolean or optional value; false means the user explicitly said no. Preserve
relative dates such as "next month" in date.description. Put hard requirements in
must_visit and softer wishes in preferences. Infer trip_type only when the request
clearly supports it. Set needs only when the user's request establishes that a search
will be needed. Do not change planning_status or ready_to_search.

Use field_resolutions to record how the user handled a question when no concrete value
was provided. Each record's field is a schema path such as "date", "duration_days", "origin",
"travelers.adults", "budget.amount", "transportation", "lodging.needed", and
"preferences". Use:
- user_unsure for "I don't know", "not sure", or equivalent.
- declined when the user refuses to answer or explicitly does not want the item.
- not_applicable when the field does not apply to this trip.
- use_recommended_default when the user says "you decide", "recommend it", or asks
  Doris to choose.
- provided only when useful for retaining an explicit resolution note; actual values
  still belong in their normal schema fields.
Keep at most one resolution record per field. Preserve existing records unless a later answer replaces them. Never turn
"I don't know" into a guessed value.

When current trip state is supplied, merge new answers into it instead of discarding
previously collected information.
""".strip()


def _conversation_text(messages: Sequence[ConversationMessage]) -> str:
    return "\n\n".join(
        f"{message.role.upper()}: {message.content}" for message in messages
    )


def parse_trip_request(
    messages: Sequence[ConversationMessage],
    current_trip: Optional[TripRequest] = None,
) -> DorisParserResult:
    if not os.getenv("OPENAI_API_KEY"):
        raise DorisConfigurationError(
            "OPENAI_API_KEY is not configured on the TravelDoris backend."
        )

    context = _conversation_text(messages)
    if current_trip is not None:
        context += "\n\nCURRENT TRIP STATE:\n" + json.dumps(
            current_trip.model_dump(mode="json"), indent=2
        )

    client = OpenAI()
    response = client.responses.parse(
        model=os.getenv("OPENAI_MODEL", "gpt-5.6-terra"),
        instructions=SYSTEM_PROMPT,
        input=context,
        text_format=DorisExtractionResult,
    )
    if response.output_parsed is None:
        raise RuntimeError("OpenAI returned no structured trip result.")
    return evaluate_trip(response.output_parsed.trip)
