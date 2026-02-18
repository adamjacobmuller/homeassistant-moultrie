"""Tests for the Moultrie Mobile API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.moultrie.api import (
    MoultrieApiClient,
    MoultrieApiError,
    MoultrieAuthError,
)
from custom_components.moultrie.const import (
    API_BASE,
    CLIENT_ID,
    SCOPE,
    TOKEN_URL,
)

from .conftest import (
    MOCK_ACCESS_TOKEN,
    MOCK_DEVICE_INFO,
    MOCK_LATEST_IMAGE,
    MOCK_REFRESH_TOKEN,
    MOCK_SETTINGS_GROUPS,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REFRESHED_ACCESS_TOKEN = "refreshed_access_token"
REFRESHED_REFRESH_TOKEN = "refreshed_refresh_token"


def _mock_response(
    status: int = 200,
    json_data: Any = None,
    read_data: bytes | None = None,
) -> MagicMock:
    """Build a fake aiohttp response usable as an async context manager."""
    resp = MagicMock()
    resp.status = status
    resp.raise_for_status = MagicMock()

    if status >= 400:
        resp.raise_for_status.side_effect = aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=status,
            message=f"HTTP {status}",
        )

    if json_data is not None:
        resp.json = AsyncMock(return_value=json_data)
        # read() returns non-empty bytes so _request knows to parse JSON
        resp.read = AsyncMock(return_value=b'{"data": true}')
    elif read_data is not None:
        resp.read = AsyncMock(return_value=read_data)
        resp.json = AsyncMock(return_value={})
    else:
        # Empty body
        resp.read = AsyncMock(return_value=b"")
        resp.json = AsyncMock(return_value={})

    return resp


def _context_manager(resp: MagicMock) -> MagicMock:
    """Wrap a response mock so it works as ``async with session.request(...) as r``."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _build_session() -> MagicMock:
    """Return a mock aiohttp.ClientSession."""
    session = MagicMock(spec=aiohttp.ClientSession)
    return session


def _build_client(session: MagicMock | None = None) -> MoultrieApiClient:
    """Return a MoultrieApiClient backed by a mock session."""
    if session is None:
        session = _build_session()
    return MoultrieApiClient(MOCK_ACCESS_TOKEN, MOCK_REFRESH_TOKEN, session)


def _token_refresh_response() -> MagicMock:
    """Return a mock response for a successful token refresh."""
    return _mock_response(
        json_data={
            "access_token": REFRESHED_ACCESS_TOKEN,
            "refresh_token": REFRESHED_REFRESH_TOKEN,
        }
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGetDevices:
    """Tests for get_devices."""

    async def test_get_devices(self) -> None:
        """Successful device list fetch returns the Devices array."""
        session = _build_session()
        api_response = {"Devices": [MOCK_DEVICE_INFO]}
        resp = _mock_response(json_data=api_response)
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        devices = await client.get_devices()

        assert devices == [MOCK_DEVICE_INFO]
        session.request.assert_called_once()
        call_args = session.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == f"{API_BASE}/api/v1/Device/Devices"

    async def test_get_devices_empty(self) -> None:
        """get_devices returns empty list when Devices key is missing."""
        session = _build_session()
        resp = _mock_response(json_data={})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        devices = await client.get_devices()

        assert devices == []


class TestGetDeviceSettings:
    """Tests for get_device_settings."""

    async def test_get_device_settings(self) -> None:
        """Successful settings fetch returns GroupedSettings list."""
        session = _build_session()
        api_response = {"GroupedSettings": MOCK_SETTINGS_GROUPS}
        resp = _mock_response(json_data=api_response)
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        settings = await client.get_device_settings(camera_id=12345)

        assert settings == MOCK_SETTINGS_GROUPS
        call_args = session.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == f"{API_BASE}/api/v1/Device/GetGroupedSettings"
        assert call_args[1]["params"] == {"id": 12345}

    async def test_get_device_settings_empty(self) -> None:
        """get_device_settings returns empty list when key is absent."""
        session = _build_session()
        resp = _mock_response(json_data={})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        settings = await client.get_device_settings(camera_id=99999)

        assert settings == []


class TestSaveDeviceSettings:
    """Tests for save_device_settings."""

    async def test_save_device_settings(self) -> None:
        """Successful save returns True."""
        session = _build_session()
        resp = _mock_response(json_data={"SettingsSaved": True})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.save_device_settings(
            camera_id=12345,
            modem_id=67890,
            settings_groups=MOCK_SETTINGS_GROUPS,
        )

        assert result is True
        call_args = session.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == f"{API_BASE}/api/v1/Device/SaveDeviceSettings"
        payload = call_args[1]["json"]
        assert payload["CameraId"] == 12345
        assert payload["ModemId"] == 67890
        assert payload["Settings"] == MOCK_SETTINGS_GROUPS

    async def test_save_device_settings_failure(self) -> None:
        """save_device_settings returns False when API does not confirm save."""
        session = _build_session()
        resp = _mock_response(json_data={"SettingsSaved": False})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.save_device_settings(
            camera_id=12345,
            modem_id=67890,
            settings_groups=MOCK_SETTINGS_GROUPS,
        )

        assert result is False


class TestRequestOnDemand:
    """Tests for request_on_demand."""

    async def test_request_on_demand(self) -> None:
        """Successful on-demand request returns the response dict."""
        session = _build_session()
        on_demand_response = {"RequestId": "abc-123", "Status": "Queued"}
        resp = _mock_response(json_data=on_demand_response)
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.request_on_demand(meid="MEID12345", event_type="image")

        assert result == on_demand_response
        call_args = session.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == f"{API_BASE}/api/v1/Device/OnDemand"
        payload = call_args[1]["json"]
        assert payload["Meid"] == "MEID12345"
        assert payload["DidConsent"] is True
        assert payload["OnDemandEventType"] == "image"

    async def test_request_on_demand_video(self) -> None:
        """On-demand request can be made for video."""
        session = _build_session()
        resp = _mock_response(json_data={"RequestId": "vid-456", "Status": "Queued"})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.request_on_demand(meid="MEID12345", event_type="video")

        payload = session.request.call_args[1]["json"]
        assert payload["OnDemandEventType"] == "video"
        assert result["RequestId"] == "vid-456"


class TestGetLatestImage:
    """Tests for get_latest_image."""

    async def test_get_latest_image_with_results(self) -> None:
        """get_latest_image returns the first image when results exist."""
        session = _build_session()
        images_response = {
            "Results": {
                "Results": [MOCK_LATEST_IMAGE],
                "TotalResults": 1,
            }
        }
        resp = _mock_response(json_data=images_response)
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        image = await client.get_latest_image(camera_id=12345)

        assert image == MOCK_LATEST_IMAGE

    async def test_get_latest_image_no_results(self) -> None:
        """get_latest_image returns None when there are no images."""
        session = _build_session()
        images_response: dict[str, Any] = {
            "Results": {
                "Results": [],
                "TotalResults": 0,
            }
        }
        resp = _mock_response(json_data=images_response)
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        image = await client.get_latest_image(camera_id=12345)

        assert image is None

    async def test_get_latest_image_missing_results_key(self) -> None:
        """get_latest_image returns None when Results key is absent."""
        session = _build_session()
        resp = _mock_response(json_data={})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        image = await client.get_latest_image(camera_id=12345)

        assert image is None


class TestHasUnreadNotifications:
    """Tests for has_unread_notifications."""

    async def test_has_unread_notifications_true(self) -> None:
        """Returns True when there are unread notifications."""
        session = _build_session()
        resp = _mock_response(json_data={"HasUnreadNotification": True})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.has_unread_notifications()

        assert result is True

    async def test_has_unread_notifications_false(self) -> None:
        """Returns False when there are no unread notifications."""
        session = _build_session()
        resp = _mock_response(json_data={"HasUnreadNotification": False})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.has_unread_notifications()

        assert result is False

    async def test_has_unread_notifications_error(self) -> None:
        """Returns False when the API call raises an exception."""
        session = _build_session()
        resp = _mock_response(status=500)
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.has_unread_notifications()

        assert result is False

    async def test_has_unread_notifications_network_error(self) -> None:
        """Returns False when a network-level error occurs."""
        session = _build_session()
        session.request = MagicMock(side_effect=aiohttp.ClientError("connection lost"))

        client = _build_client(session)
        result = await client.has_unread_notifications()

        assert result is False


class TestFetchImage:
    """Tests for fetch_image."""

    async def test_fetch_image(self) -> None:
        """Successful image download returns bytes."""
        session = _build_session()
        image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        resp = _mock_response(read_data=image_bytes)
        session.get = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.fetch_image("https://cdn.example.com/photo.jpg")

        assert result == image_bytes
        session.get.assert_called_once()
        call_args = session.get.call_args
        assert call_args[0][0] == "https://cdn.example.com/photo.jpg"

    async def test_fetch_image_error(self) -> None:
        """fetch_image raises on HTTP error."""
        session = _build_session()
        resp = _mock_response(status=404)
        session.get = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)

        with pytest.raises(aiohttp.ClientResponseError):
            await client.fetch_image("https://cdn.example.com/missing.jpg")


class TestTokenRefreshOn401:
    """Tests for automatic token refresh on 401 responses."""

    async def test_token_refresh_on_401(self) -> None:
        """_request refreshes tokens and retries when a 401 is received."""
        session = _build_session()

        # First call returns 401 (no raise_for_status side-effect -- 401 is
        # handled internally before raise_for_status is called).
        resp_401 = MagicMock()
        resp_401.status = 401
        resp_401.raise_for_status = MagicMock()
        resp_401.read = AsyncMock(return_value=b"")
        resp_401.json = AsyncMock(return_value={})

        # Token refresh response
        refresh_resp = _mock_response(
            json_data={
                "access_token": REFRESHED_ACCESS_TOKEN,
                "refresh_token": REFRESHED_REFRESH_TOKEN,
            }
        )

        # Retry after refresh returns real data
        retry_resp = _mock_response(json_data={"Devices": [MOCK_DEVICE_INFO]})

        # session.request is used by _request; session.post is used by refresh_tokens
        session.request = MagicMock(
            side_effect=[
                _context_manager(resp_401),
                _context_manager(retry_resp),
            ]
        )
        session.post = MagicMock(return_value=_context_manager(refresh_resp))

        client = _build_client(session)
        devices = await client.get_devices()

        assert devices == [MOCK_DEVICE_INFO]
        # Verify tokens were updated
        assert client.access_token == REFRESHED_ACCESS_TOKEN
        assert client.refresh_token == REFRESHED_REFRESH_TOKEN
        # session.request called twice: once for the 401, once for the retry
        assert session.request.call_count == 2
        # session.post called once for token refresh
        session.post.assert_called_once()

    async def test_token_refresh_on_401_retry_uses_new_token(self) -> None:
        """After refresh, the retry request uses the new access token."""
        session = _build_session()

        resp_401 = MagicMock()
        resp_401.status = 401
        resp_401.raise_for_status = MagicMock()
        resp_401.read = AsyncMock(return_value=b"")
        resp_401.json = AsyncMock(return_value={})

        refresh_resp = _mock_response(
            json_data={
                "access_token": REFRESHED_ACCESS_TOKEN,
                "refresh_token": REFRESHED_REFRESH_TOKEN,
            }
        )

        retry_resp = _mock_response(json_data={"Devices": []})

        session.request = MagicMock(
            side_effect=[
                _context_manager(resp_401),
                _context_manager(retry_resp),
            ]
        )
        session.post = MagicMock(return_value=_context_manager(refresh_resp))

        client = _build_client(session)
        await client.get_devices()

        # The second request call should carry the refreshed token
        retry_call = session.request.call_args_list[1]
        headers = retry_call[1]["headers"]
        assert headers["Authorization"] == f"Bearer {REFRESHED_ACCESS_TOKEN}"


class TestRefreshTokens:
    """Tests for refresh_tokens."""

    async def test_refresh_tokens(self) -> None:
        """Direct token refresh updates internal state and returns new tokens."""
        session = _build_session()
        refresh_resp = _mock_response(
            json_data={
                "access_token": REFRESHED_ACCESS_TOKEN,
                "refresh_token": REFRESHED_REFRESH_TOKEN,
            }
        )
        session.post = MagicMock(return_value=_context_manager(refresh_resp))

        client = _build_client(session)
        tokens = await client.refresh_tokens()

        assert tokens == {
            "access_token": REFRESHED_ACCESS_TOKEN,
            "refresh_token": REFRESHED_REFRESH_TOKEN,
        }
        assert client.access_token == REFRESHED_ACCESS_TOKEN
        assert client.refresh_token == REFRESHED_REFRESH_TOKEN

        # Verify the correct token endpoint was called with proper data
        session.post.assert_called_once()
        call_args = session.post.call_args
        assert call_args[0][0] == TOKEN_URL
        post_data = call_args[1]["data"]
        assert post_data["grant_type"] == "refresh_token"
        assert post_data["client_id"] == CLIENT_ID
        assert post_data["refresh_token"] == MOCK_REFRESH_TOKEN
        assert post_data["scope"] == SCOPE

    async def test_refresh_tokens_error(self) -> None:
        """refresh_tokens raises MoultrieAuthError on 400."""
        session = _build_session()
        resp = _mock_response(status=400)
        session.post = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)

        with pytest.raises(MoultrieAuthError):
            await client.refresh_tokens()

        # Tokens should not have changed
        assert client.access_token == MOCK_ACCESS_TOKEN
        assert client.refresh_token == MOCK_REFRESH_TOKEN


class TestRequestEmptyBody:
    """Tests for _request handling of empty response bodies."""

    async def test_request_empty_body_returns_empty_dict(self) -> None:
        """_request returns {} when the response body is empty."""
        session = _build_session()
        resp = _mock_response()  # defaults to empty read
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client._request("GET", "/api/v1/test")

        assert result == {}

    async def test_request_with_json_body(self) -> None:
        """_request returns parsed JSON when the body is present."""
        session = _build_session()
        resp = _mock_response(json_data={"key": "value"})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client._request("GET", "/api/v1/test")

        assert result == {"key": "value"}


class TestGetImages:
    """Tests for get_images."""

    async def test_get_images_defaults(self) -> None:
        """get_images sends correct default pagination parameters."""
        session = _build_session()
        images_response = {
            "Results": {
                "Results": [MOCK_LATEST_IMAGE],
                "TotalResults": 1,
            }
        }
        resp = _mock_response(json_data=images_response)
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        result = await client.get_images()

        assert result == images_response
        call_args = session.request.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == f"{API_BASE}/api/v2/Image/ImageSearch"
        payload = call_args[1]["json"]
        assert payload["PageSize"] == 20
        assert payload["PageNumber"] == 1
        assert "CameraId" not in payload

    async def test_get_images_with_camera_id(self) -> None:
        """get_images includes CameraId when provided."""
        session = _build_session()
        resp = _mock_response(json_data={"Results": {"Results": [], "TotalResults": 0}})
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        await client.get_images(page_size=5, page_number=2, camera_id=12345)

        payload = session.request.call_args[1]["json"]
        assert payload["PageSize"] == 5
        assert payload["PageNumber"] == 2
        assert payload["CameraId"] == 12345


class TestGetDevice:
    """Tests for get_device."""

    async def test_get_device(self) -> None:
        """Successful single device fetch."""
        session = _build_session()
        resp = _mock_response(json_data=MOCK_DEVICE_INFO)
        session.request = MagicMock(return_value=_context_manager(resp))

        client = _build_client(session)
        device = await client.get_device(camera_id=12345)

        assert device == MOCK_DEVICE_INFO
        call_args = session.request.call_args
        assert call_args[0][0] == "GET"
        assert call_args[0][1] == f"{API_BASE}/api/v1/Device/GetSingleDevice"
        assert call_args[1]["params"] == {"cameraId": 12345}


class TestHeaders:
    """Tests for the _headers helper."""

    def test_headers_contain_bearer_token(self) -> None:
        """_headers returns Authorization and Content-Type."""
        client = _build_client()
        headers = client._headers()

        assert headers == {
            "Authorization": f"Bearer {MOCK_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
