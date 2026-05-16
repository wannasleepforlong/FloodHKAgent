from datetime import datetime, timezone, timedelta

from app.agents.tide_agent import TideAgent


HKT = timezone(timedelta(hours=8))


def test_extract_latest_height_uses_hour_column_not_month_value():
    fields = ["Month", "Date", *[f"{hour:02d}" for hour in range(1, 25)]]
    row = ["05", "16", *["0.0"] * 24]
    row[2 + 16] = "2.34"  # 17:00 HKT
    table = {"fields": fields, "data": [row]}

    height = TideAgent._extract_latest_height(
        table, now=datetime(2026, 5, 16, 17, 48, tzinfo=HKT)
    )

    assert height == 2.34


def test_extract_next_peak_handles_duplicate_hlt_columns():
    table = {
        "fields": [
            "Month",
            "Date",
            "Time",
            "Height(m)",
            "Type",
            "Time",
            "Height(m)",
            "Type",
            "Time",
            "Height(m)",
            "Type",
            "Time",
            "Height(m)",
            "Type",
        ],
        "data": [
            [
                "05",
                "16",
                "03:12",
                "0.7",
                "L",
                "09:20",
                "2.4",
                "H",
                "15:40",
                "0.8",
                "L",
                "21:55",
                "2.6",
                "H",
            ]
        ],
    }

    peak = TideAgent._extract_next_peak(table, now=datetime(2026, 5, 16, 17, 48, tzinfo=HKT))

    assert peak is not None
    assert peak["time"] == "2026-05-16T21:55:00+08:00"
    assert peak["raw"]["height_m"] == 2.6
    assert peak["raw"]["type"] == "H"


def test_extract_next_peak_ignores_blank_placeholder_columns():
    table = {
        "fields": ["Month", "Date", "Time", "Height(m)", "Type", "Time", "Height(m)", "Type"],
        "data": [["05", "16", "09:20", "2.4", "H", "", "", ""]],
    }

    peak = TideAgent._extract_next_peak(table, now=datetime(2026, 5, 16, 8, 0, tzinfo=HKT))

    assert peak is not None
    assert peak["time"] == "2026-05-16T09:20:00+08:00"
