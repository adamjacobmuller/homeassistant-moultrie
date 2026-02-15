# Moultrie Mobile for Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=adamjacobmuller&repository=homeassistant-moultrie&category=integration)

A custom [Home Assistant](https://www.home-assistant.io/) integration for [Moultrie Mobile](https://www.moultriemobile.com/) trail cameras. Monitor your cameras, view images, adjust settings, and trigger on-demand captures directly from Home Assistant.

## Features

- **Camera entity** with latest image display and caching
- **On-demand photo and video capture** via button press
- **Full camera settings control** (capture mode, resolution, upload frequency, PIR sensitivity, and more)
- **Battery, signal, storage, and temperature monitoring**
- **Subscription and device status tracking**
- **Automatic token refresh** with reauth flow if credentials expire
- **Dynamic device detection** -- new cameras appear automatically, removed cameras are cleaned up

## Installation

### HACS (Recommended)

1. Click the badge above, or go to **HACS > Integrations > Custom Repositories**
2. Add `https://github.com/adamjacobmuller/homeassistant-moultrie` as a custom repository (category: Integration)
3. Install **Moultrie Mobile**
4. Restart Home Assistant

### Manual

1. Copy `custom_components/moultrie/` into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for **Moultrie Mobile**
3. Enter your Moultrie Mobile email and password

The integration authenticates via Moultrie's Azure AD B2C PKCE flow and automatically refreshes tokens. If your session expires, Home Assistant will prompt you to re-authenticate.

## Entities

Each Moultrie camera creates the following entities:

### Camera

| Entity | Description |
|--------|-------------|
| Trail Camera | Displays the latest captured image with caching |

**Extra attributes:** `taken_on`, `temperature`, `on_demand`, `flash`, `image_url`, `enhanced_image_url`

### Sensors

| Entity | Unit | Description |
|--------|------|-------------|
| Battery | % | Device battery level |
| Signal Strength | % | Cellular signal strength |
| Storage Free | GB | Available SD card storage |
| Storage Total | GB | Total SD card capacity |
| Images Used | count | Images used on current subscription plan |
| Firmware | -- | Current firmware version |
| Last Activity | timestamp | When the camera last reported in |
| Temperature | °F | Temperature at time of last image capture |

### Binary Sensors

| Entity | Description |
|--------|-------------|
| Subscription Active | Whether the subscription plan is active |
| Device Active | Whether the device is actively reporting |
| On Demand Enabled | Whether on-demand capture is enabled on the device |
| Pending Settings | Whether the device has settings waiting to sync |

### Switches

| Entity | Description |
|--------|-------------|
| On Demand | Toggle on-demand capture capability |
| Motion Freeze | Toggle motion freeze mode |

### Selects

| Entity | Description |
|--------|-------------|
| Capture Mode | Time lapse, motion detect, or both |
| Photo/Video Mode | Photo, video, or photo & video |
| Upload Frequency | How often images are uploaded to the cloud |
| Photo Resolution | Image quality setting |
| Multi-Shot | Number of photos per trigger event |
| Video Resolution | Video quality (720p, 1080p) |
| PIR Sensitivity | Motion sensor sensitivity (low, medium, high) |
| Power Source | Battery type (AA, solar, external) |

Options are dynamically populated from the camera's reported capabilities.

### Buttons

| Entity | Description |
|--------|-------------|
| Request Photo | Trigger an immediate on-demand photo |
| Request Video | Trigger an immediate on-demand video |

Buttons only appear when the camera supports on-demand capture. The video button requires video upload capability.

## Polling

The integration polls the Moultrie API every **5 minutes** for device status, images, and settings. This matches the typical upload interval for trail cameras and avoids excessive API usage.

## Diagnostics

The integration supports Home Assistant's diagnostics download. Sensitive data (email, password, tokens, serial numbers, MEIDs) is automatically redacted.

## Requirements

- Home Assistant 2024.1 or newer
- A Moultrie Mobile account with at least one registered camera
- An active Moultrie Mobile subscription

## License

MIT
