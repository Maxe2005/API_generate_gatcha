"""
Tests unitaires pour l'authentification minimale (app.core.security / app.clients.auth_api).

Ne nécessite ni base de données ni services externes : les appels HTTP vers
l'API d'authentification sont simulés avec httpx.MockTransport.
"""

import json

import httpx
import pytest
from fastapi import HTTPException

from app.clients.auth_api import (
    AuthApiClient,
    AuthServiceUnavailableError,
    AuthTokenInvalidError,
)
from app.core.security import require_auth
from app.core import security as security_module

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _patch_transport(monkeypatch, handler):
    """Redirige tous les httpx.AsyncClient créés par auth_api vers un transport simulé."""

    class _PatchedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.clients.auth_api.httpx.AsyncClient", _PatchedAsyncClient)


class TestAuthApiClient:
    async def test_verify_token_success_returns_user(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/user/verify-token"
            assert json.loads(request.content) == {"token": "abc"}
            return httpx.Response(200, json={"username": "alice", "role": "ADMIN"})

        _patch_transport(monkeypatch, handler)
        client = AuthApiClient(base_url="http://auth.test")

        assert await client.verify_token("abc") == "alice"

    async def test_verify_token_401_raises_invalid(self, monkeypatch):
        _patch_transport(monkeypatch, lambda request: httpx.Response(401))
        client = AuthApiClient(base_url="http://auth.test")

        with pytest.raises(AuthTokenInvalidError):
            await client.verify_token("bad-token")

    async def test_verify_token_403_raises_invalid(self, monkeypatch):
        _patch_transport(monkeypatch, lambda request: httpx.Response(403))
        client = AuthApiClient(base_url="http://auth.test")

        with pytest.raises(AuthTokenInvalidError):
            await client.verify_token("bad-token")

    async def test_verify_token_500_raises_invalid(self, monkeypatch):
        # L'API auth renvoie aujourd'hui un 500 (bug connu) pour un token
        # malformé au lieu d'un 401/403 ; on le traite comme "invalide" par
        # fail-safe (même logique que l'AuthInterceptor Java), pas comme une
        # panne du service.
        _patch_transport(monkeypatch, lambda request: httpx.Response(500))
        client = AuthApiClient(base_url="http://auth.test")

        with pytest.raises(AuthTokenInvalidError):
            await client.verify_token("abc")

    async def test_verify_token_network_error_raises_unavailable(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        _patch_transport(monkeypatch, handler)
        client = AuthApiClient(base_url="http://auth.test")

        with pytest.raises(AuthServiceUnavailableError):
            await client.verify_token("abc")


class TestRequireAuthDependency:
    async def test_missing_credentials_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization=None, x_internal_api_key=None)
        assert exc_info.value.status_code == 401

    async def test_valid_bearer_token_returns_context(self, monkeypatch):
        settings = security_module.get_settings()
        monkeypatch.setattr(settings, "INTERNAL_API_KEY", "")

        def handler(request: httpx.Request) -> httpx.Response:
            assert json.loads(request.content) == {"token": "my-token"}
            return httpx.Response(200, json={"username": "bob"})

        _patch_transport(monkeypatch, handler)

        ctx = await require_auth(authorization="Bearer my-token", x_internal_api_key=None)
        assert ctx.username == "bob"
        assert ctx.token == "my-token"

    async def test_invalid_bearer_token_raises_401(self, monkeypatch):
        _patch_transport(monkeypatch, lambda request: httpx.Response(401))

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization="Bearer bad", x_internal_api_key=None)
        assert exc_info.value.status_code == 401

    async def test_auth_service_down_raises_500(self, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        _patch_transport(monkeypatch, handler)

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization="Bearer whatever", x_internal_api_key=None)
        assert exc_info.value.status_code == 500

    async def test_internal_api_key_bypasses_token_check(self, monkeypatch):
        settings = security_module.get_settings()
        monkeypatch.setattr(settings, "INTERNAL_API_KEY", "s3cret")

        ctx = await require_auth(authorization=None, x_internal_api_key="s3cret")
        assert ctx.username == "internal-service"
        assert ctx.token is None

    async def test_wrong_internal_api_key_raises_401(self, monkeypatch):
        settings = security_module.get_settings()
        monkeypatch.setattr(settings, "INTERNAL_API_KEY", "s3cret")

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(authorization=None, x_internal_api_key="wrong")
        assert exc_info.value.status_code == 401
