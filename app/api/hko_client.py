from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from app.api.endpoints import (
    DEFAULT_LANG,
    HOURLY_RAINFALL_BASE_URL,
    OPENDATA_API_BASE_URL,
    OPENDATA_DATA_TYPES,
    WEATHER_API_BASE_URL,
    WEATHER_DATA_TYPES,
)
from app.settings import Settings


class HKOClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._client = httpx.AsyncClient(
            timeout=settings.hko_timeout_seconds,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get_json(self, url: str, params: dict[str, Any]) -> Any:
        last_error: Exception | None = None
        for _ in range(self.settings.hko_retries + 1):
            try:
                response = await self._client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    async def get_local_weather_forecast(self, lang: str = DEFAULT_LANG) -> dict[str, Any]:
        return await self._get_json(
            WEATHER_API_BASE_URL,
            {"dataType": WEATHER_DATA_TYPES["flw"], "lang": lang},
        )

    async def get_nine_day_forecast(self, lang: str = DEFAULT_LANG) -> dict[str, Any]:
        return await self._get_json(
            WEATHER_API_BASE_URL,
            {"dataType": WEATHER_DATA_TYPES["fnd"], "lang": lang},
        )

    async def get_current_weather_report(self, lang: str = DEFAULT_LANG) -> dict[str, Any]:
        return await self._get_json(
            WEATHER_API_BASE_URL,
            {"dataType": WEATHER_DATA_TYPES["rhrread"], "lang": lang},
        )

    async def get_warning_summary(self, lang: str = DEFAULT_LANG) -> dict[str, Any]:
        return await self._get_json(
            WEATHER_API_BASE_URL,
            {"dataType": WEATHER_DATA_TYPES["warnsum"], "lang": lang},
        )

    async def get_warning_info(self, lang: str = DEFAULT_LANG) -> dict[str, Any]:
        return await self._get_json(
            WEATHER_API_BASE_URL,
            {"dataType": WEATHER_DATA_TYPES["warningInfo"], "lang": lang},
        )

    async def get_hourly_tide_heights(
        self,
        station: str,
        *,
        year: int,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "dataType": OPENDATA_DATA_TYPES["HHOT"],
            "rformat": "json",
            "station": station,
            "year": year,
        }
        if month is not None:
            params["month"] = month
        if day is not None:
            params["day"] = day
        if hour is not None:
            params["hour"] = hour
        return await self._get_json(OPENDATA_API_BASE_URL, params)

    async def get_high_low_tides(
        self,
        station: str,
        *,
        year: int,
        month: int | None = None,
        day: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "dataType": OPENDATA_DATA_TYPES["HLT"],
            "rformat": "json",
            "station": station,
            "year": year,
        }
        if month is not None:
            params["month"] = month
        if day is not None:
            params["day"] = day
        return await self._get_json(OPENDATA_API_BASE_URL, params)

    async def get_lightning_count(self, lang: str = DEFAULT_LANG) -> dict[str, Any]:
        return await self._get_json(
            OPENDATA_API_BASE_URL,
            {
                "dataType": OPENDATA_DATA_TYPES["LHL"],
                "rformat": "json",
                "lang": lang,
            },
        )

    async def get_hourly_rainfall(self, lang: str = DEFAULT_LANG) -> dict[str, Any]:
        return await self._get_json(HOURLY_RAINFALL_BASE_URL, {"lang": lang})

    async def get_tide_bundle(self, now: datetime) -> dict[str, Any]:
        stations = ["QUB", "TBT", "CCH"]
        bundle: dict[str, Any] = {"as_of": now.isoformat(), "stations": {}}
        for station in stations:
            bundle["stations"][station] = {
                "hhot": await self.get_hourly_tide_heights(
                    station, year=now.year, month=now.month
                ),
                "hlt": await self.get_high_low_tides(station, year=now.year, month=now.month),
            }
        return bundle
