"""Shared fixtures for Moultrie Mobile tests."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.moultrie.const import (
    CONF_ACCESS_TOKEN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

MOCK_EMAIL = "test@example.com"
MOCK_PASSWORD = "testpassword123"
MOCK_ACCESS_TOKEN = "mock_access_token"
MOCK_REFRESH_TOKEN = "mock_refresh_token"

MOCK_DEVICE_INFO: dict[str, Any] = {
    "DeviceId": 12345,
    "DeviceName": "Test Camera",
    "DisplayName": "Moultrie Delta Cellular",
    "Model": "MCG-14072",
    "SerialNumber": "SN123456",
    "SoftwareVersion": "4.20",
    "DeviceBatteryLevel": 85,
    "SignalStrength": 70,
    "FreeStorageBytes": 5368709120,
    "TotalStorageBytes": 16106127360,
    "IsActive": True,
    "OnDemandSwitchSetting": True,
    "CanUploadVideo": True,
    "HasPendingSettingsUpdates": False,
    "LatestActivity": "2024-01-15T10:30:00Z",
    "MEID": "MEID12345",
    "ModemId": 67890,
    "Subscription": {
        "PlanName": "Elite",
        "TotalImagesUsed": 1500,
        "IsPendingCancellation": False,
    },
}

MOCK_LATEST_IMAGE: dict[str, Any] = {
    "imageUrl": "https://cdn.example.com/image1.jpg",
    "enhancedImageUrl": "https://cdn.example.com/image1_enhanced.jpg",
    "takenOn": "2024-01-15T08:00:00Z",
    "temperature": "45",
    "IsOnDemand": False,
    "flash": False,
}

MOCK_SETTINGS_GROUPS: list[dict[str, Any]] = [
    {
        "GroupName": "Camera",
        "Settings": [
            {
                "SettingShortText": "CTD",
                "Name": "Capture Mode",
                "Value": "T",
                "Options": [
                    {"Text": "Time Lapse", "Value": "T"},
                    {"Text": "Motion Detect", "Value": "M"},
                    {"Text": "Both", "Value": "B"},
                ],
            },
            {
                "SettingShortText": "CCM",
                "Name": "Photo/Video",
                "Value": "P",
                "Options": [
                    {"Text": "Photo", "Value": "P"},
                    {"Text": "Video", "Value": "V"},
                    {"Text": "Photo & Video", "Value": "B"},
                ],
            },
            {
                "SettingShortText": "CCR",
                "Name": "Photo Resolution",
                "Value": "H",
                "Options": [
                    {"Text": "High", "Value": "H"},
                    {"Text": "Low", "Value": "L"},
                ],
            },
            {
                "SettingShortText": "CMS",
                "Name": "Multi-Shot",
                "Value": "1",
                "Options": [
                    {"Text": "1 Photo", "Value": "1"},
                    {"Text": "2 Photos", "Value": "2"},
                    {"Text": "3 Photos", "Value": "3"},
                ],
            },
            {
                "SettingShortText": "CVR",
                "Name": "Video Resolution",
                "Value": "720",
                "Options": [
                    {"Text": "720p", "Value": "720"},
                    {"Text": "1080p", "Value": "1080"},
                ],
            },
            {
                "SettingShortText": "CPR",
                "Name": "PIR Sensitivity",
                "Value": "M",
                "Options": [
                    {"Text": "Low", "Value": "L"},
                    {"Text": "Medium", "Value": "M"},
                    {"Text": "High", "Value": "H"},
                ],
            },
            {
                "SettingShortText": "CFF",
                "Name": "Motion Freeze",
                "Value": "T",
                "Options": [],
            },
        ],
    },
    {
        "GroupName": "Modem",
        "Settings": [
            {
                "SettingShortText": "MTI",
                "Name": "Upload Frequency",
                "Value": "4",
                "Options": [
                    {"Text": "Hourly", "Value": "1"},
                    {"Text": "Every 4 Hours", "Value": "4"},
                    {"Text": "Twice Daily", "Value": "12"},
                ],
            },
            {
                "SettingShortText": "ODE",
                "Name": "On Demand",
                "Value": "T",
                "Options": [],
            },
            {
                "SettingShortText": "BAT",
                "Name": "Power Source",
                "Value": "AA",
                "Options": [
                    {"Text": "AA Batteries", "Value": "AA"},
                    {"Text": "Solar", "Value": "SOL"},
                    {"Text": "External", "Value": "EXT"},
                ],
            },
        ],
    },
]


def _build_settings_map(
    settings_groups: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Build flat settings lookup from grouped settings."""
    settings_map: dict[str, dict[str, Any]] = {}
    for group in settings_groups:
        for setting in group.get("Settings", []):
            short = setting.get("SettingShortText")
            if short:
                settings_map[short] = setting
    return settings_map


MOCK_COORDINATOR_DATA: dict[str, Any] = {
    "devices": {
        12345: {
            "info": MOCK_DEVICE_INFO,
            "latest_image": MOCK_LATEST_IMAGE,
            "settings_groups": MOCK_SETTINGS_GROUPS,
            "settings": _build_settings_map(MOCK_SETTINGS_GROUPS),
        },
    },
}


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title=f"Moultrie ({MOCK_EMAIL})",
        data={
            CONF_EMAIL: MOCK_EMAIL,
            CONF_PASSWORD: MOCK_PASSWORD,
            CONF_ACCESS_TOKEN: MOCK_ACCESS_TOKEN,
            CONF_REFRESH_TOKEN: MOCK_REFRESH_TOKEN,
        },
        source="user",
        unique_id=MOCK_EMAIL,
    )
    return entry


@pytest.fixture
def mock_api_client() -> MagicMock:
    """Create a mock API client."""
    client = MagicMock()
    client.access_token = MOCK_ACCESS_TOKEN
    client.refresh_token = MOCK_REFRESH_TOKEN
    client.get_devices = AsyncMock(return_value=[MOCK_DEVICE_INFO])
    client.get_latest_image = AsyncMock(return_value=MOCK_LATEST_IMAGE)
    client.get_device_settings = AsyncMock(return_value=MOCK_SETTINGS_GROUPS)
    client.save_device_settings = AsyncMock(return_value=True)
    client.request_on_demand = AsyncMock(return_value={})
    client.get_account = AsyncMock(return_value={"AccountId": "acc123"})
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_login() -> Generator[AsyncMock, None, None]:
    """Mock the login static method."""
    with patch(
        "custom_components.moultrie.config_flow.MoultrieApiClient.login",
        new_callable=AsyncMock,
        return_value={
            "access_token": MOCK_ACCESS_TOKEN,
            "refresh_token": MOCK_REFRESH_TOKEN,
        },
    ) as mock:
        yield mock


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock, None, None]:
    """Mock setting up the integration."""
    with patch(
        "custom_components.moultrie.async_setup_entry",
        return_value=True,
    ) as mock:
        yield mock
