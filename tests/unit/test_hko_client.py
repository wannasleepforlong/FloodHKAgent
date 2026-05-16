import httpx
import pytest

from app.api.hko_client import HKOClient
from app.settings import get_settings


@pytest.mark.asyncio
async def test_hko_client_requests_expected_endpoint():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["dataType"] == "flw"
        return httpx.Response(200, json={"generalSituation": "Fine"})

    client = HKOClient(settings=get_settings(), transport=httpx.MockTransport(handler))
    try:
        payload = await client.get_local_weather_forecast()
    finally:
        await client.aclose()
    assert payload["generalSituation"] == "Fine"
