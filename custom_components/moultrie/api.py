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

import requests

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

    def __init__(self, access_token: str, refresh_token: str) -> None:
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._session = requests.Session()

    @property
    def access_token(self) -> str:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    @staticmethod
    def login(email: str, password: str) -> dict[str, str]:
        """Perform full PKCE login flow. Returns dict with access_token and refresh_token."""
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        state = secrets.token_urlsafe(16)
        nonce = secrets.token_urlsafe(16)

        session = requests.Session()

        # Step 1: GET authorize page for CSRF token and transaction ID
        resp = session.get(
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
        )
        resp.raise_for_status()

        settings_match = re.search(r"var SETTINGS\s*=\s*(\{.*?\});", resp.text, re.DOTALL)
        if not settings_match:
            raise MoultrieAuthError("Could not find SETTINGS on B2C login page")

        settings = json.loads(settings_match.group(1))
        csrf = settings["csrf"]
        trans_id = settings["transId"]
        policy_path = settings["hosts"]["policy"]

        # Step 2: POST credentials
        resp = session.post(
            f"{B2C_HOST}/{TENANT_ID}/{policy_path}/SelfAsserted",
            params={"tx": trans_id, "p": policy_path},
            headers={
                "X-CSRF-TOKEN": csrf,
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
            },
            data={
                "request_type": "RESPONSE",
                "signInName": email,
                "password": password,
            },
        )
        resp.raise_for_status()
        sa_result = resp.json()
        if sa_result.get("status") != "200":
            raise MoultrieAuthError(f"Login failed: {sa_result}")

        # Step 3: Follow redirect to get auth code
        resp = session.get(
            f"{B2C_HOST}/{TENANT_ID}/{policy_path}/api/CombinedSigninAndSignup/confirmed",
            params={
                "rememberMe": "false",
                "csrf_token": csrf,
                "tx": trans_id,
                "p": policy_path,
            },
            allow_redirects=False,
        )
        if resp.status_code not in (301, 302):
            raise MoultrieAuthError(f"Expected redirect, got {resp.status_code}")

        location = resp.headers["Location"]
        frag_params = urllib.parse.parse_qs(urllib.parse.urlparse(location).fragment)
        if "code" not in frag_params:
            raise MoultrieAuthError("No authorization code in redirect")
        code = frag_params["code"][0]

        # Step 4: Exchange code for tokens
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
                "scope": SCOPE,
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }

    def refresh_tokens(self) -> dict[str, str]:
        """Refresh the access token using the refresh token."""
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": self._refresh_token,
                "scope": SCOPE,
            },
        )
        resp.raise_for_status()
        tokens = resp.json()
        self._access_token = tokens["access_token"]
        self._refresh_token = tokens["refresh_token"]
        return {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
        }

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an API request, refreshing token on 401."""
        url = f"{API_BASE}{path}"
        resp = self._session.request(method, url, headers=self._headers(), **kwargs)
        if resp.status_code == 401:
            _LOGGER.debug("Token expired, refreshing")
            self.refresh_tokens()
            resp = self._session.request(method, url, headers=self._headers(), **kwargs)
        resp.raise_for_status()
        if not resp.content:
            return {}
        return resp.json()

    def _get(self, path: str, params: dict | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, data: dict | None = None) -> Any:
        return self._request("POST", path, json=data)

    # --- Account ---

    def get_account(self) -> dict:
        return self._get("/api/v1/Account/AccountDetails", params={"Update": "false"})

    # --- Devices ---

    def get_devices(self) -> list[dict]:
        result = self._get("/api/v1/Device/Devices")
        return result.get("Devices", [])

    def get_device(self, camera_id: int) -> dict:
        return self._get("/api/v1/Device/GetSingleDevice", params={"cameraId": camera_id})

    def get_device_settings(self, camera_id: int) -> list[dict]:
        result = self._get("/api/v1/Device/GetGroupedSettings", params={"id": camera_id})
        return result.get("GroupedSettings", [])

    def save_device_settings(
        self,
        camera_id: int,
        modem_id: int,
        settings_groups: list[dict],
    ) -> bool:
        """Save settings by sending the full grouped settings structure.

        The API requires the complete GetGroupedSettings structure back,
        with modified values, plus CameraId and ModemId.
        """
        result = self._post(
            "/api/v1/Device/SaveDeviceSettings",
            {
                "CameraId": camera_id,
                "ModemId": modem_id,
                "Settings": settings_groups,
            },
        )
        return result.get("SettingsSaved", False)

    # --- On-Demand ---

    def request_on_demand(self, meid: str, event_type: str = "image") -> dict:
        return self._post(
            "/api/v1/Device/OnDemand",
            {"Meid": meid, "DidConsent": True, "OnDemandEventType": event_type},
        )

    # --- Images ---

    def get_images(
        self,
        page_size: int = 20,
        page_number: int = 1,
        camera_id: int | None = None,
    ) -> dict:
        body: dict[str, Any] = {"PageSize": page_size, "PageNumber": page_number}
        if camera_id is not None:
            body["CameraId"] = camera_id
        return self._post("/api/v2/Image/ImageSearch", body)

    def get_latest_image(self, camera_id: int) -> dict | None:
        result = self.get_images(page_size=1, page_number=1, camera_id=camera_id)
        results = result.get("Results", {}).get("Results", [])
        return results[0] if results else None

    def get_pending_requests(self, device_id: int) -> dict:
        return self._get(
            "/api/v1/Image/GetPendingVideoAndHighResIds",
            params={"deviceId": device_id},
        )

    # --- Notifications ---

    def has_unread_notifications(self) -> bool:
        try:
            result = self._get("/api/v1/NotificationCenter/HasUnreadNotification")
            return result.get("HasUnreadNotification", False)
        except Exception:
            return False
