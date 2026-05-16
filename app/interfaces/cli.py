from __future__ import annotations

import argparse
import asyncio

from app.models.schemas import RunMode
from app.services.orchestrator import FloodSwarmOrchestrator
from app.settings import get_settings


async def _run(pretty: bool, output_path: str | None) -> int:
    orchestrator = FloodSwarmOrchestrator(settings=get_settings())
    try:
        result = await orchestrator.run(mode=RunMode.LIVE)
    finally:
        await orchestrator.aclose()
    rendered = result.model_dump_json(indent=2 if pretty else None)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    print(rendered)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="run-alert")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--output", help="Optional file path for the JSON output")
    args = parser.parse_args()
    return asyncio.run(_run(pretty=args.pretty, output_path=args.output))


if __name__ == "__main__":
    raise SystemExit(main())
