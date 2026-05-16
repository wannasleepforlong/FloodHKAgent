from __future__ import annotations

import argparse
import asyncio
from typing import Any

from app.services.letta import Letta, LettaLearningClient
from app.settings import Settings, get_settings


def _mask(value: str | None) -> str:
    if not value:
        return "missing"
    if len(value) <= 8:
        return "***set***"
    return f"{value[:4]}...{value[-4:]}"


def _diagnose(settings: Settings) -> list[str]:
    checks = [
        f"letta-client installed: {'yes' if Letta is not None else 'no'}",
        f"FLOOD_SWARM_LETTA_LEARNING_ENABLED: {settings.letta_learning_enabled}",
        f"FLOOD_SWARM_LETTA_AGENT_ID: {_mask(settings.letta_agent_id)}",
        f"LETTA_API_KEY: {_mask(settings.letta_api_key)}",
        f"LETTA_BASE_URL: {_mask(settings.letta_base_url)}",
        f"FLOOD_SWARM_PREDICTION_HORIZON_MINUTES: {settings.prediction_horizon_minutes}",
    ]
    return checks


async def _run(args: argparse.Namespace) -> int:
    settings = get_settings()
    client = LettaLearningClient(settings)

    print("Letta smoke test")
    print("================")
    for line in _diagnose(settings):
        print(f"- {line}")
    print(f"- client enabled: {client.enabled}")

    missing: list[str] = []
    if Letta is None:
        missing.append("Install `letta-client` in the active environment.")
    if not settings.letta_learning_enabled:
        missing.append("Set `FLOOD_SWARM_LETTA_LEARNING_ENABLED=true`.")
    if not settings.letta_agent_id:
        missing.append("Set `FLOOD_SWARM_LETTA_AGENT_ID` to the target Letta agent id.")
    if not (settings.letta_api_key or settings.letta_base_url):
        missing.append("Set `LETTA_API_KEY` or `LETTA_BASE_URL`.")

    if missing:
        print("\nConfiguration issues detected:")
        for item in missing:
            print(f"- {item}")
        return 1

    try:
        summary = await client.fetch_learning_summary()
    except Exception as exc:
        print(f"\nSummary fetch failed: {exc}")
        return 2

    print("\nSummary fetch succeeded.")
    print(f"Summary: {summary or '[empty response]'}")

    if args.skip_write:
        print("\nSkipping lesson write because --skip-write was provided.")
        return 0

    lesson_text = (
        "Smoke test lesson for HK flood swarm Letta integration.\n"
        f"- horizon_minutes: {settings.prediction_horizon_minutes}\n"
        "- purpose: verify that lesson persistence is configured correctly\n"
        "- note: this can be ignored or deleted from memory if undesired"
    )

    try:
        acknowledgement = await client.store_validation_lesson(lesson_text)
    except Exception as exc:
        print(f"\nLesson write failed: {exc}")
        return 3

    print("\nLesson write succeeded.")
    print(f"Acknowledgement: {acknowledgement or '[empty response]'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the Letta learning integration.")
    parser.add_argument(
        "--skip-write",
        action="store_true",
        help="Only test summary retrieval and skip writing a lesson to Letta memory.",
    )
    args = parser.parse_args()
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
