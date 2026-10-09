import time
from  unittest.mock import AsyncMock

import pytest
import jwt
import httpx

from src.initial_client import InitialClient


def test_initial_client_is_singleton(initial_client):
    client = InitialClient(
        base_url="http://another-url",
        service_id="service_id_2",
        service_token="service_token_2",
        gateway_name="gateway_name_2",
        access_token_expire_sec=100,
        jwt_secret="jwt_secret_2",
        )

    assert initial_client is client
    assert client.service_id == "service_id"


def test_get_headers(initial_client):
    headers = initial_client._get_headers("user-context")

    assert headers == {
        "X-Service-ID": "service_id",
        "X-Service-Token": "service_token",
        "X-User-Context": "user-context",
    }

def test_build_user_context_valid_claims(initial_client):
    claims = {
        "id": 123,
        "is_active": True,
        "is_superuser": False,
        }

    before = int(time.time())
    token = initial_client._build_user_context(claims)
    after = int(time.time())

    payload = jwt.decode(
        token,
        "jwt_secret",
        algorithms=["HS256"],
        audience="gateway_name",
    )

    assert payload["sub"] == "123"
    assert payload["is_active"] is True
    assert payload["is_superuser"] is False
    assert payload["aud"] == "gateway_name"
    assert before + 50 <= payload["exp"] <= after + 50


@pytest.mark.parametrize(
    "claims",
    [
        None,
        {},
        {"is_active": True, "is_superuser": False},
        {"id": 123, "is_superuser": False},
        {"id": 123, "is_active": True},
    ],
)
def test_build_user_context_invalid_claims(initial_client, claims):
    with pytest.raises(RuntimeError):
        initial_client._build_user_context(claims)



@pytest.mark.anyio
async def test_request_success(initial_client):
    response = httpx.Response(
        200,
        json={"ok": True},
        request=httpx.Request("GET", "http://localhost/test"),
        )
    initial_client.client.request = AsyncMock(return_value=response)

    result = await initial_client._request(
        method="GET",
        path="/test",
        user_context="test-token",
        params={"id": 123},
    )

    assert result.status_code == 200
    assert result.json() == {"ok": True}

    initial_client.client.request.assert_awaited_once_with(
        "GET",
        "/test",
        headers={
            "X-Service-ID": "service_id",
            "X-Service-Token": "service_token",
            "X-User-Context": "test-token",
        },
        params={"id": 123},
    )

@pytest.mark.anyio
async def test_request_http_error(initial_client):
    response = httpx.Response(
        500,
        request=httpx.Request("GET", "http://localhost/test"),
        )
    initial_client.client.request = AsyncMock(return_value=response)

    with pytest.raises(httpx.HTTPStatusError):
        await initial_client._request(
            method="GET",
            path="/test",
            user_context="test-token",
        )


@pytest.mark.anyio
async def test_request_connection_error(initial_client):
    initial_client.client.request = AsyncMock(
    side_effect=httpx.ConnectError("Connection failed")
    )

    with pytest.raises(httpx.ConnectError, match="Connection failed"):
        await initial_client._request(
            method="GET",
            path="/test",
            user_context="test-token",
        )


@pytest.mark.anyio
async def test_request_timeout(initial_client):
    initial_client.client.request = AsyncMock(
    side_effect=httpx.TimeoutException("Request timed out")
    )

    with pytest.raises(httpx.TimeoutException, match="Request timed out"):
        await initial_client._request(
            method="GET",
            path="/test",
            user_context="test-token",
        )


@pytest.mark.anyio
async def test_close(initial_client):
    initial_client.client.aclose = AsyncMock()
    await initial_client.close()
    initial_client.client.aclose.assert_awaited_once()
