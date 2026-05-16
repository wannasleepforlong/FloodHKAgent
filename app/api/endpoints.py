from __future__ import annotations

WEATHER_API_BASE_URL = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
OPENDATA_API_BASE_URL = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
HOURLY_RAINFALL_BASE_URL = "https://data.weather.gov.hk/weatherAPI/opendata/hourlyRainfall.php"

DEFAULT_LANG = "en"

WEATHER_DATA_TYPES = {
    "flw": "flw",
    "fnd": "fnd",
    "rhrread": "rhrread",
    "warnsum": "warnsum",
    "warningInfo": "warningInfo",
}

OPENDATA_DATA_TYPES = {
    "HHOT": "HHOT",
    "HLT": "HLT",
    "LHL": "LHL",
}
