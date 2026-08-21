"""Interactive CLI to exercise Doris until the trip is ready, then dump JSON.

Run from the repo root:

    python -m backend.scripts.test_doris_chat
"""

from __future__ import annotations

import json
import sys

from dotenv import load_dotenv

from backend.models.trip import ConversationMessage, TripRequest
from backend.services.doris_parser import DorisConfigurationError, parse_trip_request
from backend.services.mock_research import research_trip


READY_STATUSES = {"ready_for_research", "ready_for_itinerary"}


def is_ready_status(status: str) -> bool:
    return status in READY_STATUSES


def prompt_yes_no(prompt: str) -> bool:
    return input(f"{prompt} [y/N]: ").strip().lower() in {"y", "yes"}


def run_confirmed_research(result) -> None:
    print("\nReady. Trip brief:\n")
    print(json.dumps(result.trip.model_dump(mode="json"), indent=2))

    if not prompt_yes_no("Run mock research for this trip now?"):
        print("Research skipped. Your trip brief is ready.")
        return

    if result.deferred_fields:
        fields = ", ".join(field.replace(".", " ") for field in result.deferred_fields)
        if not prompt_yes_no(f"Accept Doris's flexible assumptions for {fields}?"):
            print("Research skipped because the deferred assumptions were not accepted.")
            return

    research = research_trip(result.trip)
    print("\nMock research results:\n")
    print(json.dumps(research.model_dump(mode="json"), indent=2))


def main() -> int:
    load_dotenv()
    print("Doris test chat. Type your trip plans. Ctrl+C or 'quit' to exit.\n")

    messages: list[ConversationMessage] = []
    current_trip: TripRequest | None = None

    try:
        while True:
            user_text = input("You: ").strip()
            if not user_text:
                continue
            if user_text.lower() in {"quit", "exit", "q"}:
                print("Bye.")
                return 0

            messages.append(ConversationMessage(role="user", content=user_text))

            try:
                result = parse_trip_request(messages, current_trip)
            except DorisConfigurationError as exc:
                print(f"Config error: {exc}", file=sys.stderr)
                return 1

            current_trip = result.trip

            if is_ready_status(result.status):
                run_confirmed_research(result)
                return 0

            question = result.clarification_question
            if not question:
                print("\nNo further clarification is required. Full result:\n")
                print(json.dumps(result.model_dump(mode="json"), indent=2))
                return 0
            print(f"Doris: {question}\n")
            messages.append(ConversationMessage(role="assistant", content=question))

    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
