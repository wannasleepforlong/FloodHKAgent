from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.config.data import ALL_DISTRICTS, DISTRICT_STATION_MAP
from app.models.schemas import AlertLevel


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_iso8601(value: str | None) -> datetime:
    if not value:
        return utc_now()
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def add_minutes(value: datetime, minutes: int) -> datetime:
    return value + timedelta(minutes=minutes)


def abs_minutes_between(left: datetime, right: datetime) -> float:
    return abs((left - right).total_seconds()) / 60.0


def season_for_month(month: int) -> str:
    if month in {6, 7, 8, 9, 10, 11}:
        return "typhoon season"
    if month in {3, 4, 5}:
        return "mei-yu / spring transition"
    return "winter / dry season"


def clamp_score(value: float) -> float:
    return max(0.0, min(10.0, round(value, 2)))


def score_to_alert_level(score: float) -> AlertLevel:
    if score >= 9:
        return AlertLevel.BLACK
    if score >= 7:
        return AlertLevel.RED
    if score >= 5:
        return AlertLevel.AMBER
    if score >= 3:
        return AlertLevel.YELLOW
    return AlertLevel.GREEN


def all_district_scores(default: float = 0.0) -> dict[str, float]:
    return {district: default for district in ALL_DISTRICTS}


def station_to_districts(station_id: str) -> list[str]:
    return [
        district for district, station_ids in DISTRICT_STATION_MAP.items() if station_id in station_ids
    ]


def safe_float(value: Any) -> float | None:
    if value in (None, "", "M"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
