"""
Tests unitaires pour FalImageClient (app.clients.fal_client).

Ne nécessite ni base de données ni services externes réels : tous les appels
HTTP sont simulés avec httpx.MockTransport (même pattern que test_security.py).
"""

import base64
import json

import httpx
import pytest

from app.clients.fal_client import FalApiError, FalImageClient

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


class _DummyMinioClient:
    """Stub pour éviter toute connexion MinIO réelle pendant les tests."""

    pass


@pytest.fixture
def fal_client(monkeypatch):
    monkeypatch.setattr("app.clients.fal_client.MinioClientWrapper", _DummyMinioClient)
    client = FalImageClient()
    # Boucles courtes/rapides pour ne pas ralentir la suite de tests
    client.max_retries = 2
    client.retry_delay = 0
    client.poll_interval = 0
    client.max_poll_attempts = 3
    return client


def _patch_transport(monkeypatch, handler):
    """Redirige tous les httpx.AsyncClient créés par fal_client vers un transport simulé."""

    class _PatchedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.clients.fal_client.httpx.AsyncClient", _PatchedAsyncClient)


class TestSubmit:
    async def test_submit_success(self, fal_client, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/fal-ai/flux/dev"
            assert request.headers["Authorization"].startswith("Key ")
            assert json.loads(request.content) == {"prompt": "a cat"}
            return httpx.Response(
                200,
                json={
                    "request_id": "abc",
                    "status_url": "https://queue.fal.run/status",
                    "response_url": "https://queue.fal.run/result",
                },
            )

        _patch_transport(monkeypatch, handler)
        result = await fal_client._submit("fal-ai/flux/dev", {"prompt": "a cat"})
        assert result["request_id"] == "abc"

    async def test_submit_retries_then_succeeds(self, fal_client, monkeypatch):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] < 2:
                return httpx.Response(500, text="boom")
            return httpx.Response(
                200,
                json={"request_id": "abc", "status_url": "u", "response_url": "u"},
            )

        _patch_transport(monkeypatch, handler)
        result = await fal_client._submit("fal-ai/flux/dev", {"prompt": "a cat"})
        assert calls["n"] == 2
        assert result["request_id"] == "abc"

    async def test_submit_exhausts_retries_raises(self, fal_client, monkeypatch):
        _patch_transport(monkeypatch, lambda request: httpx.Response(500, text="boom"))

        with pytest.raises(FalApiError):
            await fal_client._submit("fal-ai/flux/dev", {"prompt": "a cat"})

    async def test_submit_network_error_raises(self, fal_client, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        _patch_transport(monkeypatch, handler)

        with pytest.raises(FalApiError):
            await fal_client._submit("fal-ai/flux/dev", {"prompt": "a cat"})


class TestPollUntilComplete:
    async def test_poll_completes(self, fal_client, monkeypatch):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            status = "IN_PROGRESS" if calls["n"] < 2 else "COMPLETED"
            return httpx.Response(200, json={"status": status})

        _patch_transport(monkeypatch, handler)
        await fal_client._poll_until_complete("https://queue.fal.run/status")
        assert calls["n"] == 2

    async def test_poll_failed_raises(self, fal_client, monkeypatch):
        _patch_transport(
            monkeypatch, lambda request: httpx.Response(200, json={"status": "FAILED"})
        )

        with pytest.raises(FalApiError):
            await fal_client._poll_until_complete("https://queue.fal.run/status")

    async def test_poll_timeout_raises(self, fal_client, monkeypatch):
        _patch_transport(
            monkeypatch, lambda request: httpx.Response(200, json={"status": "IN_PROGRESS"})
        )

        with pytest.raises(FalApiError):
            await fal_client._poll_until_complete("https://queue.fal.run/status")


class TestReferenceImageEncoding:
    def test_to_data_uri_encodes_base64(self, fal_client):
        data_uri = fal_client._to_data_uri(b"hello", content_type="image/webp")
        assert data_uri.startswith("data:image/webp;base64,")
        encoded = data_uri.split(",", 1)[1]
        assert base64.b64decode(encoded) == b"hello"


class TestRunGeneration:
    async def test_run_generation_downloads_image_bytes(self, fal_client, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if request.url.path == "/fal-ai/flux/dev":
                return httpx.Response(
                    200,
                    json={
                        "request_id": "abc",
                        "status_url": "https://queue.fal.run/status",
                        "response_url": "https://queue.fal.run/result",
                    },
                )
            if url == "https://queue.fal.run/status":
                return httpx.Response(200, json={"status": "COMPLETED"})
            if url == "https://queue.fal.run/result":
                return httpx.Response(
                    200, json={"images": [{"url": "https://cdn.fal.run/image.png"}]}
                )
            if url == "https://cdn.fal.run/image.png":
                return httpx.Response(200, content=b"fake-image-bytes")
            raise AssertionError(f"Unexpected request: {url}")

        _patch_transport(monkeypatch, handler)
        raw_bytes = await fal_client._run_generation("fal-ai/flux/dev", {"prompt": "a cat"})
        assert raw_bytes == b"fake-image-bytes"

    async def test_run_generation_missing_status_url_raises(self, fal_client, monkeypatch):
        _patch_transport(
            monkeypatch, lambda request: httpx.Response(200, json={"request_id": "abc"})
        )

        with pytest.raises(FalApiError):
            await fal_client._run_generation("fal-ai/flux/dev", {"prompt": "a cat"})

    async def test_run_generation_no_images_raises(self, fal_client, monkeypatch):
        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if request.url.path == "/fal-ai/flux/dev":
                return httpx.Response(
                    200,
                    json={
                        "request_id": "abc",
                        "status_url": "https://queue.fal.run/status",
                        "response_url": "https://queue.fal.run/result",
                    },
                )
            if url == "https://queue.fal.run/status":
                return httpx.Response(200, json={"status": "COMPLETED"})
            if url == "https://queue.fal.run/result":
                return httpx.Response(200, json={"images": []})
            raise AssertionError(f"Unexpected request: {url}")

        _patch_transport(monkeypatch, handler)
        with pytest.raises(FalApiError):
            await fal_client._run_generation("fal-ai/flux/dev", {"prompt": "a cat"})


class TestGeneratePixelArt:
    async def test_generate_pixel_art_with_reference_image_uses_image_to_image_payload(
        self, fal_client, monkeypatch
    ):
        captured_payload = {}

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if "image-to-image" in request.url.path:
                captured_payload.update(json.loads(request.content))
                return httpx.Response(
                    200,
                    json={
                        "request_id": "abc",
                        "status_url": "https://queue.fal.run/status",
                        "response_url": "https://queue.fal.run/result",
                    },
                )
            if url == "https://queue.fal.run/status":
                return httpx.Response(200, json={"status": "COMPLETED"})
            if url == "https://queue.fal.run/result":
                return httpx.Response(
                    200, json={"images": [{"url": "https://cdn.fal.run/image.png"}]}
                )
            if url == "https://cdn.fal.run/image.png":
                return httpx.Response(200, content=b"fake-image-bytes")
            raise AssertionError(f"Unexpected request: {url}")

        _patch_transport(monkeypatch, handler)
        monkeypatch.setattr(
            "app.clients.fal_client.store_generated_image",
            lambda raw_bytes, filename_base, minio_client: {
                "image_url": "http://minio/x.webp",
                "raw_image_key": "monsters/x.png",
            },
        )

        result = await fal_client.generate_pixel_art(
            "a fire dragon", "dragon", reference_image_bytes=b"ref-bytes"
        )

        assert result == {"image_url": "http://minio/x.webp", "raw_image_key": "monsters/x.png"}
        assert captured_payload["image_url"].startswith("data:image/png;base64,")
