"""Tests for the Moultrie Mobile binary sensor platform."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from custom_components.moultrie.binary_sensor import (
    _device_active,
    _on_demand_enabled,
    _pending_settings,
    _subscription_active,
)

from .conftest import MOCK_COORDINATOR_DATA


def _device_data(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a deep copy of the first device's data with optional info overrides."""
    data = copy.deepcopy(MOCK_COORDINATOR_DATA["devices"][12345])
    if overrides:
        data["info"].update(overrides)
    return data


# -- subscription_active -----------------------------------------------------


def test_subscription_active_true() -> None:
    """Active subscription with PlanName and no pending cancellation returns True."""
    data = _device_data()
    assert _subscription_active(data) is True


def test_subscription_active_pending_cancellation() -> None:
    """Subscription with IsPendingCancellation=True returns False."""
    data = _device_data(
        {"Subscription": {"PlanName": "Elite", "IsPendingCancellation": True}}
    )
    assert _subscription_active(data) is False


def test_subscription_active_no_plan() -> None:
    """Subscription with PlanName=None returns None (unknown)."""
    data = _device_data(
        {"Subscription": {"PlanName": None, "IsPendingCancellation": False}}
    )
    assert _subscription_active(data) is None


# -- device_active ------------------------------------------------------------


def test_device_active() -> None:
    """Device with IsActive=True returns True."""
    data = _device_data()
    assert _device_active(data) is True


# -- on_demand_enabled --------------------------------------------------------


def test_on_demand_enabled() -> None:
    """Device with OnDemandSwitchSetting=True returns True."""
    data = _device_data()
    assert _on_demand_enabled(data) is True


# -- pending_settings ---------------------------------------------------------


def test_pending_settings() -> None:
    """Device with HasPendingSettingsUpdates=False returns False."""
    data = _device_data()
    assert _pending_settings(data) is False


# -- missing data -------------------------------------------------------------


def test_values_with_missing_data() -> None:
    """All value functions return None when their keys are absent from info."""
    data: dict[str, Any] = {"info": {}}

    assert _subscription_active(data) is None
    assert _device_active(data) is None
    assert _on_demand_enabled(data) is None
    assert _pending_settings(data) is None
