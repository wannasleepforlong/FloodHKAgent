from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _parse_generated_at(value: str | None, fallback_stem: str) -> str:
    if not value:
        return f"run_{fallback_stem}.txt"
    normalized = value.replace("Z", "+00:00")
    try:
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        safe_value = "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")
        return f"run_{safe_value or fallback_stem}.txt"
    return f"run_{timestamp.strftime('%Y%m%d_%H%M%S_%fZ')}.txt"


def _to_pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True)


def _append_section(lines: list[str], title: str, body: str | list[str]) -> None:
    lines.append(title)
    lines.append("-" * len(title))
    if isinstance(body, list):
        lines.extend(body)
    else:
        lines.append(body)
    lines.append("")


def _format_agent(signal: dict[str, Any]) -> list[str]:
    lines = [
        f"Agent: {signal.get('agent_id', 'Unknown')}",
        f"Data source: {signal.get('data_source', 'Unknown')}",
        f"Data freshness: {signal.get('data_freshness', 'Unknown')}",
        "Ingested from HKO APIs:",
        _to_pretty_json(signal.get("raw_extracts", {})),
        "",
        "Agent output:",
        f"Risk score: {signal.get('risk_score', 'Unknown')}",
        f"Confidence: {signal.get('confidence', 'Unknown')}",
        f"Primary driver: {signal.get('primary_driver', 'Unknown')}",
        f"Affected districts: {', '.join(signal.get('affected_districts', [])) or 'None'}",
        f"Flags: {', '.join(signal.get('flags', [])) or 'None'}",
        f"Reasoning: {signal.get('reasoning', '')}",
        f"Latency ms: {signal.get('latency_ms', 'Unknown')}",
        f"Is stale: {signal.get('is_stale', False)}",
    ]
    if signal.get("peer_queries_issued"):
        lines.extend(
            [
                "",
                "Peer queries issued:",
                _to_pretty_json(signal["peer_queries_issued"]),
            ]
        )
    if signal.get("peer_responses_received"):
        lines.extend(
            [
                "",
                "Peer responses received:",
                _to_pretty_json(signal["peer_responses_received"]),
            ]
        )
    return lines


def _format_final_output(payload: dict[str, Any]) -> list[str]:
    actions = payload.get("recommended_actions", [])
    action_lines = [
        f"- {item.get('code', 'UNKNOWN')}: {item.get('description', '')}" for item in actions
    ] or ["- None"]
    return [
        f"Run ID: {payload.get('run_id', 'Unknown')}",
        f"Generated at: {payload.get('generated_at', 'Unknown')}",
        f"Alert level: {payload.get('alert_level', 'Unknown')}",
        f"Overall risk score: {payload.get('overall_risk_score', 'Unknown')}",
        f"Confidence overall: {payload.get('confidence_overall', 'Unknown')}",
        f"Next update priority: {payload.get('next_update_priority', 'Unknown')}",
        f"Top risk districts: {', '.join(payload.get('top_risk_districts', [])) or 'None'}",
        "",
        "Compound flags:",
        _to_pretty_json(payload.get("compound_flags", [])),
        "",
        "Compound detector output:",
        _to_pretty_json(payload.get("compound_detector_output", [])),
        "",
        "District scores:",
        _to_pretty_json(payload.get("district_scores", {})),
        "",
        "Narrative (EN):",
        payload.get("narrative_en", ""),
        "",
        "Narrative (TC):",
        payload.get("narrative_tc", ""),
        "",
        "Recommended actions:",
        *action_lines,
        "",
        "Reasoning:",
        payload.get("reasoning", ""),
        "",
        "System health:",
        _to_pretty_json(payload.get("system_health", {})),
        "",
        "Prediction window:",
        _to_pretty_json(payload.get("prediction_window")),
        "",
        "Validation:",
        _to_pretty_json(payload.get("validation")),
    ]


def export_run_txts(log_dir: Path) -> list[Path]:
    written: list[Path] = []
    for json_path in sorted(log_dir.glob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        txt_name = _parse_generated_at(payload.get("generated_at"), json_path.stem)
        txt_path = log_dir / txt_name

        lines: list[str] = []
        _append_section(
            lines,
            "Run Summary",
            [
                f"Source JSON: {json_path.name}",
                f"Output TXT: {txt_name}",
                f"Generated at: {payload.get('generated_at', 'Unknown')}",
            ],
        )

        for index, signal in enumerate(payload.get("agent_signals", []), start=1):
            _append_section(lines, f"Agent {index}", _format_agent(signal))

        _append_section(lines, "Final Output", _format_final_output(payload))
        txt_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        written.append(txt_path)
    return written


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    log_dir = project_root / "logs"
    written = export_run_txts(log_dir)
    print(f"Exported {len(written)} run text files to {log_dir}")


if __name__ == "__main__":
    main()
