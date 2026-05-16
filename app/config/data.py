from __future__ import annotations

DISTRICT_STATION_MAP: dict[str, list[str]] = {
    "Yuen Long": ["RF001", "RF002", "N12"],
    "Tuen Mun": ["RF019"],
    "North": ["RF015", "RF016", "RF017"],
    "Tai Po": ["RF004", "RF005"],
    "Sha Tin": ["RF020"],
    "Sai Kung": ["RF006", "RF007", "N15"],
    "Eastern": ["RF008", "RF009", "RF026"],
    "Islands": ["RF010", "RF011", "RF012", "RF013", "RF014"],
    "Kwun Tong": ["K03", "RF008"],
    "Kowloon City": ["RF025"],
    "Sham Shui Po": ["RF022"],
    "Yau Tsim Mong": ["K02"],
    "Wong Tai Sin": ["RF025", "K09"],
    "Kwai Tsing": ["RF018", "RF021"],
    "Tsuen Wan": ["RF018"],
    "Central & Western": ["RF023", "RF027"],
    "Wan Chai": ["RF027", "H17"],
    "Southern": ["H15", "H24", "RF028"],
}

ALL_DISTRICTS: list[str] = sorted(DISTRICT_STATION_MAP.keys())

RAIN_THRESHOLDS_MM = {
    "amber": 30,
    "red": 50,
    "black": 70,
}

TIDE_GAUGES = {
    "QUB": {
        "station_name": "Quarry Bay",
        "districts": ["Eastern", "Wan Chai", "Central & Western"],
        "mhhw": 2.22,
        "danger_zone": 2.5,
    },
    "TBT": {
        "station_name": "Tsim Bei Tsui",
        "districts": ["Yuen Long", "Tuen Mun", "North"],
        "mhhw": 2.06,
        "danger_zone": 2.4,
    },
    "CCH": {
        "station_name": "Cheung Chau",
        "districts": ["Islands", "Southern"],
        "mhhw": 1.85,
        "danger_zone": 2.1,
    },
}

COMPOUND_RULES: dict[str, str] = {
    "RAIN_TIDE": "Heavy rainfall coinciding with a near-term high tide window.",
    "RAIN_TIDE_TYPHOON": "Heavy rainfall, dangerous tide timing, and tropical cyclone impacts.",
    "CONVECTIVE_IMMINENT": "Lightning activity suggests near-term rainfall escalation.",
    "DEEP_BAY_SURGE": "Tsim Bei Tsui tide heights indicate elevated Deep Bay flooding risk.",
    "DEGRADED_CONFIDENCE": "Multiple upstream agents relied on stale or fallback data.",
}

RECOMMENDED_ACTION_LIBRARY: dict[str, str] = {
    "MONITOR": "Continue monitoring. No immediate operational action is required.",
    "ALERT_DRAINS": "Notify drainage services to inspect and clear likely blockage points.",
    "EVACUATION_ADVISORY": "Prepare advisory messaging for low-lying and flood-prone communities.",
    "CLOSE_UNDERPASSES": "Coordinate with transport authorities on underpass and low-road assessments.",
    "ACTIVATE_FLOOD_BARRIERS": "Prepare or deploy temporary flood barriers at known hotspots.",
    "SUSPEND_CONSTRUCTION": "Advise hillside and excavation sites to suspend hazardous work.",
    "COASTAL_WARNING": "Issue a coastal flooding advisory for exposed shoreline districts.",
    "EMERGENCY_RESPONSE": "Escalate to emergency response coordination and district-level readiness.",
}

FLOOD_RELEVANT_WARNING_CODES: set[str] = {
    "WRAINA",
    "WRAINR",
    "WRAINB",
    "WFNTSA",
    "WL",
    "TC1",
    "TC3",
    "TC8NE",
    "TC8SE",
    "TC8NW",
    "TC8SW",
    "TC9",
    "TC10",
    "CANCEL",
    "WTS",
    "WMSGNL",
}
