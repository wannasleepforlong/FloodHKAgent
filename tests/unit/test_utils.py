from app.models.schemas import AlertLevel
from app.services.utils import parse_iso8601, score_to_alert_level, station_to_districts


def test_station_to_districts_returns_expected_matches():
    assert station_to_districts("RF019") == ["Tuen Mun"]
    assert "Kwun Tong" in station_to_districts("RF008")


def test_score_to_alert_level_mapping():
    assert score_to_alert_level(1.9) == AlertLevel.GREEN
    assert score_to_alert_level(3.0) == AlertLevel.YELLOW
    assert score_to_alert_level(5.1) == AlertLevel.AMBER
    assert score_to_alert_level(7.3) == AlertLevel.RED
    assert score_to_alert_level(9.0) == AlertLevel.BLACK


def test_parse_iso8601_handles_z_suffix():
    parsed = parse_iso8601("2026-05-16T00:00:00Z")
    assert parsed.year == 2026
    assert parsed.tzinfo is not None
