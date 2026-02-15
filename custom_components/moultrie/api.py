"""Moultrie Mobile API client."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import re
import secrets
import urllib.parse
from typing import Any

import aiohttp

from .const import (
    API_BASE,
    B2C_HOST,
    CLIENT_ID,
    POLICY,
    REDIRECT_URI,
    SCOPE,
    TENANT_ID,
    TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)


class MoultrieAuthError(Exception):
    """Authentication error."""


class MoultrieApiError(Exception):
    """API request error."""


class MoultrieApiClient:
    """Client for the Moultrie Mobile API."""

    def __init__(
        self,
        access_token: str,
        refresh_token: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Initialize the API client."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._session = session

    @property
    def access_token(self) -> str:
        """Return the current access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str:
        """Return the current refresh token."""
        return self._refresh_token

    @staticmethod
    def _extract_cookies(
        resp: aiohttp.ClientResponse, cookies: dict[str, str]
    ) -> dict[str, str]:
        """Extract Set-Cookie values from raw headers into a dict.

        Azure B2C uses cookie names containing ``|`` which aiohttp's
        CookieJar silently drops.  We handle cookies manually instead.
        """
        merged = dict(cookies)
        for key, val in resp.raw_headers:
            if key.lower() == b"set-cookie":
                name_value = val.decode("utf-8", errors="replace").split(";")[0]
                name, _, value = name_value.partition("=")
                merged[name] = value
        return merged

    @staticmethod
    def _cookie_header(cookies: dict[str, str]) -> str:
        return "; ".join(f"{k}={v}" for k, v in cookies.items())

    @staticmethod
    async def login(
        email: str, password: str, session: aiohttp.ClientSession
    ) -> dict[str, str]:
        """Perform full PKCE login flow.

        Uses a dedicated session with DummyCookieJar and manual cookie
        handling because Azure B2C sets cookies with ``|`` in the name
        which aiohttp's CookieJar silently drops.

        Returns dict with access_token and refresh_token.
        """
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)
        cookies: dict[str, str] = {}

        # Use a dedicated session to avoid cookie jar conflicts with HA's
        # shared session.  We handle B2C cookies manually via headers.
        async with aiohttp.ClientSession(
            cookie_jar=aiohttp.DummyCookieJar()
        ) as login_session:
            return await MoultrieApiClient._do_login(
                email, password, login_session, verifier, challenge, state, nonce
            )

    @staticmethod
    async def _do_login(
        email: str,
        password: str,
        session: aiohttp.ClientSession,
        verifier: str,
        challenge: str,
        state: str,
        nonce: str,
    ) -> dict[str, str]:
        """Execute the PKCE login steps with manual cookie handling."""
        cookies: dict[str, str] = {}

        # Step 1: GET authorize page for CSRF token and transaction ID
        async with session.get(
            f"{B2C_HOST}/{TENANT_ID}/oauth2/v2.0/authorize",
            params={
                "p": POLICY,
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "response_type": "code",
                "scope": SCOPE,
                "response_mode": "fragment",
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "nonce": nonce,
                "state": state,
            },
        ) as resp:
            resp.raise_for_status()
            page_text = await resp.text()
            cookies = MoultrieApiClient._extract_cookies(resp, cookies)

        settings_match = re.search(r"var SETTINGS\s*=\s*(\{.*?\});", page_text, re.DOTALL)
        if not settings_match:
            raise MoultrieAuthError("Could not find SETTINGS on B2C login page")

        settings = json.loads(settings_match.group(1))
        csrf: str = settings["csrf"]
        trans_id: str = settings["transId"]
        policy_path: str = settings["hosts"]["policy"]

        # Step 2: POST credentials
        async with session.post(
            f"{B2C_HOST}/{TENANT_ID}/{policy_path}/SelfAsserted",
            params={"tx": trans_id, "p": policy_path},
            headers={
                "X-CSRF-TOKEN": csrf,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "Cookie": MoultrieApiClient._cookie_header(cookies),
            },
            data={
                "request_type": "RESPONSE",
                "signInName": email,
                "password": password,
            },
        ) as resp:
            resp.raise_for_status()
            sa_result = await resp.json(content_type=None)
            cookies = MoultrieApiClient._extract_cookies(resp, cookies)

        if sa_result.get("status") != "200":
            raise MoultrieAuthError(f"Login failed: {sa_result}")

        # Step 3: Follow redirect to get auth code
        async with session.get(
            f"{B2C_HOST}/{TENANT_ID}/{policy_path}/api/CombinedSigninAndSignup/confirmed",
            params={
                "rememberMe": "false",
                "csrf_token": csrf,
                "tx": trans_id,
                "p": policy_path,
            },
            headers={"Cookie": MoultrieApiClient._cookie_header(cookies)},
            allow_redirects=False,
        ) as resp:
            if resp.status not in (301, 302):
                raise MoultrieAuthError(f"Expected redirect, got {resp.status}")
            location = resp.headers["Location"]

        frag_params = urllib.parse.parse_qs(urllib.parse.urlparse(location).fragment)
        if "code" not in frag_params:
            raise MoultrieAuthError("No authorization code in redirect")
        code = frag_params["code"][0]

        # Step 4: Exchange code for tokens
        async with session.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
                "scope": SCOPE,
            },
        ) as resp:
            resp.raise_for_status()
            tokens = await resp.json()

        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }

    async def refresh_tokens(self) -> dict[str, str]:
        """Refresh the access token using the refresh token."""
        async with self._session.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": self._refresh_token,
                "scope": SCOPE,
            },
        ) as resp:
            resp.raise_for_status()
            tokens = await resp.json()

        self._access_token = tokens["access_token"]
        self._refresh_token = tokens["refresh_token"]
        return {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
        }

    def _headers(self) -> dict[str, str]:
        """Return auth headers."""
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an API request, refreshing token on 401."""
        url = f"{API_BASE}{path}"
        async with self._session.request(
            method, url, headers=self._headers(), **kwargs
        ) as resp:
            if resp.status == 401:
                _LOGGER.debug("Token expired, refreshing")
                await self.refresh_tokens()
                async with self._session.request(
                    method, url, headers=self._headers(), **kwargs
                ) as resp2:
                    resp2.raise_for_status()
                    if not await resp2.read():
                        return {}
                    return await resp2.json()
            resp.raise_for_status()
            if not await resp.read():
                return {}
            return await resp.json()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Make a GET request."""
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, data: dict[str, Any] | None = None) -> Any:
        """Make a POST request."""
        return await self._request("POST", path, json=data)

    # --- Account ---

    async def get_account(self) -> dict[str, Any]:
        """Get account details."""
        result = await self._get("/api/v1/Account/AccountDetails", params={"Update": "false"})
        return result  # type: ignore[no-any-return]

    # --- Devices ---

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get all devices."""
        result = await self._get("/api/v1/Device/Devices")
        return result.get("Devices", [])  # type: ignore[no-any-return]

    async def get_device(self, camera_id: int) -> dict[str, Any]:
        """Get a single device."""
        result = await self._get(
            "/api/v1/Device/GetSingleDevice", params={"cameraId": camera_id}
        )
        return result  # type: ignore[no-any-return]

    async def get_device_settings(self, camera_id: int) -> list[dict[str, Any]]:
        """Get grouped settings for a device."""
        result = await self._get(
            "/api/v1/Device/GetGroupedSettings", params={"id": camera_id}
        )
        return result.get("GroupedSettings", [])  # type: ignore[no-any-return]

    async def save_device_settings(
        self,
        camera_id: int,
        modem_id: int,
        settings_groups: list[dict[str, Any]],
    ) -> bool:
        """Save settings by sending the full grouped settings structure."""
        result = await self._post(
            "/api/v1/Device/SaveDeviceSettings",
            {
                "CameraId": camera_id,
                "ModemId": modem_id,
                "Settings": settings_groups,
            },
        )
        return result.get("SettingsSaved", False)  # type: ignore[no-any-return]

    # --- On-Demand ---

    async def request_on_demand(
        self, meid: str, event_type: str = "image"
    ) -> dict[str, Any]:
        """Request an on-demand photo or video."""
        result = await self._post(
            "/api/v1/Device/OnDemand",
            {"Meid": meid, "DidConsent": True, "OnDemandEventType": event_type},
        )
        return result  # type: ignore[no-any-return]

    # --- Images ---

    async def get_images(
        self,
        page_size: int = 20,
        page_number: int = 1,
        camera_id: int | None = None,
    ) -> dict[str, Any]:
        """Search for images."""
        body: dict[str, Any] = {"PageSize": page_size, "PageNumber": page_number}
        if camera_id is not None:
            body["CameraId"] = camera_id
        result = await self._post("/api/v2/Image/ImageSearch", body)
        return result  # type: ignore[no-any-return]

    async def get_latest_image(self, camera_id: int) -> dict[str, Any] | None:
        """Get the latest image for a camera."""
        result = await self.get_images(page_size=1, page_number=1, camera_id=camera_id)
        results = result.get("Results", {}).get("Results", [])
        return results[0] if results else None

    async def get_pending_requests(self, device_id: int) -> dict[str, Any]:
        """Get pending video and high-res requests."""
        result = await self._get(
            "/api/v1/Image/GetPendingVideoAndHighResIds",
            params={"deviceId": device_id},
        )
        return result  # type: ignore[no-any-return]

    # --- Notifications ---

    async def has_unread_notifications(self) -> bool:
        """Check for unread notifications."""
        try:
            result = await self._get("/api/v1/NotificationCenter/HasUnreadNotification")
            return result.get("HasUnreadNotification", False)  # type: ignore[no-any-return]
        except Exception:
            return False

    async def fetch_image(self, url: str) -> bytes:
        """Fetch an image from a URL."""
        async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            resp.raise_for_status()
            return await resp.read()
