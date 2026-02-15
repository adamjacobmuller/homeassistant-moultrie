"""Tests for the Moultrie Mobile camera platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.moultrie.camera import MoultrieCamera
from tests.conftest import MOCK_COORDINATOR_DATA, MOCK_LATEST_IMAGE


@pytest.fixture
def mock_coordinator() -> MagicMock:
    """Create a mock coordinator."""
    coordinator = MagicMock()
    coordinator.data = MOCK_COORDINATOR_DATA
    coordinator.client = MagicMock()
    coordinator.client.fetch_image = AsyncMock(return_value=b"fake_image_data")

    def get_device_data(device_id: int) -> dict | None:
        if coordinator.data is None:
            return None
        return coordinator.data.get("devices", {}).get(device_id)

    coordinator.get_device_data = get_device_data
    return coordinator


class TestMoultrieCamera:
    """Test Moultrie camera entity."""

    def test_extra_state_attributes(self, mock_coordinator: MagicMock) -> None:
        """Test extra state attributes from latest image."""
        camera = MoultrieCamera(mock_coordinator, 12345)
        attrs = camera.extra_state_attributes

        assert attrs["taken_on"] == "2024-01-15T08:00:00Z"
        assert attrs["temperature"] == "45"
        assert attrs["image_url"] == "https://cdn.example.com/image1.jpg"
        assert attrs["enhanced_image_url"] == "https://cdn.example.com/image1_enhanced.jpg"
        assert "on_demand" not in attrs  # IsOnDemand is False
        assert "flash" not in attrs  # flash is False

    def test_extra_state_attributes_no_image(self, mock_coordinator: MagicMock) -> None:
        """Test extra state attributes when no latest image."""
        mock_coordinator.data = {"devices": {12345: {"info": {}, "latest_image": None, "settings_groups": [], "settings": {}}}}
        camera = MoultrieCamera(mock_coordinator, 12345)
        assert camera.extra_state_attributes == {}

    def test_extra_state_attributes_no_device(self, mock_coordinator: MagicMock) -> None:
        """Test extra state attributes when device data is None."""
        mock_coordinator.data = {"devices": {}}
        camera = MoultrieCamera(mock_coordinator, 12345)
        assert camera.extra_state_attributes == {}

    def test_extra_state_attributes_on_demand(self, mock_coordinator: MagicMock) -> None:
        """Test on_demand attribute when IsOnDemand is True."""
        import copy
        data = copy.deepcopy(MOCK_COORDINATOR_DATA)
        data["devices"][12345]["latest_image"]["IsOnDemand"] = True
        data["devices"][12345]["latest_image"]["flash"] = True
        mock_coordinator.data = data
        camera = MoultrieCamera(mock_coordinator, 12345)
        attrs = camera.extra_state_attributes
        assert attrs["on_demand"] is True
        assert attrs["flash"] is True

    @pytest.mark.asyncio
    async def test_camera_image_fetch(self, mock_coordinator: MagicMock) -> None:
        """Test fetching camera image."""
        camera = MoultrieCamera(mock_coordinator, 12345)
        camera.hass = MagicMock()

        result = await camera.async_camera_image()
        assert result == b"fake_image_data"
        mock_coordinator.client.fetch_image.assert_called_once_with(
            "https://cdn.example.com/image1.jpg"
        )

    @pytest.mark.asyncio
    async def test_camera_image_cached(self, mock_coordinator: MagicMock) -> None:
        """Test that image is cached when URL hasn't changed."""
        camera = MoultrieCamera(mock_coordinator, 12345)
        camera.hass = MagicMock()

        # First fetch
        result1 = await camera.async_camera_image()
        assert result1 == b"fake_image_data"
        assert mock_coordinator.client.fetch_image.call_count == 1

        # Second fetch - should use cache
        result2 = await camera.async_camera_image()
        assert result2 == b"fake_image_data"
        assert mock_coordinator.client.fetch_image.call_count == 1

    @pytest.mark.asyncio
    async def test_camera_image_new_url(self, mock_coordinator: MagicMock) -> None:
        """Test that new image is fetched when URL changes."""
        camera = MoultrieCamera(mock_coordinator, 12345)
        camera.hass = MagicMock()

        # First fetch
        await camera.async_camera_image()
        assert mock_coordinator.client.fetch_image.call_count == 1

        # Change URL
        import copy
        new_data = copy.deepcopy(MOCK_COORDINATOR_DATA)
        new_data["devices"][12345]["latest_image"]["imageUrl"] = "https://cdn.example.com/image2.jpg"
        mock_coordinator.data = new_data
        mock_coordinator.client.fetch_image = AsyncMock(return_value=b"new_image_data")

        result = await camera.async_camera_image()
        assert result == b"new_image_data"
        mock_coordinator.client.fetch_image.assert_called_once_with(
            "https://cdn.example.com/image2.jpg"
        )

    @pytest.mark.asyncio
    async def test_camera_image_fetch_error(self, mock_coordinator: MagicMock) -> None:
        """Test that cached image is returned on fetch error."""
        camera = MoultrieCamera(mock_coordinator, 12345)
        camera.hass = MagicMock()

        # First successful fetch
        await camera.async_camera_image()

        # Simulate error on next fetch with new URL
        import copy
        new_data = copy.deepcopy(MOCK_COORDINATOR_DATA)
        new_data["devices"][12345]["latest_image"]["imageUrl"] = "https://cdn.example.com/broken.jpg"
        mock_coordinator.data = new_data
        mock_coordinator.client.fetch_image = AsyncMock(side_effect=Exception("Network error"))

        result = await camera.async_camera_image()
        # Should return the cached image from the first fetch
        assert result == b"fake_image_data"

    @pytest.mark.asyncio
    async def test_camera_image_no_data(self, mock_coordinator: MagicMock) -> None:
        """Test camera image when no device data."""
        mock_coordinator.data = {"devices": {}}
        camera = MoultrieCamera(mock_coordinator, 12345)
        camera.hass = MagicMock()

        result = await camera.async_camera_image()
        assert result is None

    @pytest.mark.asyncio
    async def test_camera_image_no_url(self, mock_coordinator: MagicMock) -> None:
        """Test camera image when no imageUrl."""
        import copy
        data = copy.deepcopy(MOCK_COORDINATOR_DATA)
        del data["devices"][12345]["latest_image"]["imageUrl"]
        mock_coordinator.data = data
        camera = MoultrieCamera(mock_coordinator, 12345)
        camera.hass = MagicMock()

        result = await camera.async_camera_image()
        assert result is None

    def test_unique_id(self, mock_coordinator: MagicMock) -> None:
        """Test unique ID format."""
        camera = MoultrieCamera(mock_coordinator, 12345)
        assert camera.unique_id == "12345_camera"

    def test_translation_key(self, mock_coordinator: MagicMock) -> None:
        """Test translation key."""
        camera = MoultrieCamera(mock_coordinator, 12345)
        assert camera._attr_translation_key == "trail_camera"
