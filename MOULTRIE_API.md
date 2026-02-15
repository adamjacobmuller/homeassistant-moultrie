# Moultrie Mobile API Reference

Complete API documentation reverse-engineered from the Moultrie Mobile Android app (v5.31.0, .NET MAUI Blazor)
and the web portal at `app.moultriemobile.com`. Covers authentication through full camera control.

---

## Table of Contents

1. [Authentication](#authentication)
2. [Base URLs](#base-urls)
3. [Account](#account)
4. [Device / Camera Management](#device--camera-management)
5. [On-Demand Photo & Video](#on-demand-photo--video)
6. [Image / Gallery](#image--gallery)
7. [Albums](#albums)
8. [Notifications](#notifications)
9. [Feature Flags](#feature-flags)
10. [Camera Settings Reference](#camera-settings-reference)
11. [Image CDN](#image-cdn)
12. [Other Services](#other-services)
13. [BLE (Bluetooth) Configuration](#ble-bluetooth-configuration)
14. [Quick Start Example](#quick-start-example)

---

## Authentication

**Provider**: Azure AD B2C (MSAL)
**Auth Flow**: PKCE Authorization Code (no ROPC / password grant support)

### Credentials

| Field | Value |
|-------|-------|
| Email | See `MOULTRIE_EMAIL` in `.env` |
| Password | See `MOULTRIE_PASSWORD` in `.env` |

### Key Parameters

| Parameter | Value |
|-----------|-------|
| B2C Hostname | `login.moultriemobile.com` |
| Tenant | `moultriemobile.onmicrosoft.com` |
| Tenant ID | `46148adf-3109-46fc-ac67-9b17d664afc3` |
| Policy | `B2C_1A_SIGNUP_SIGNIN` |
| Password Reset Policy | `B2C_1A_PASSWORDRESET` |
| Scope | `https://moultriemobile.onmicrosoft.com/9e848fa3-9069-4bf0-bcc3-ab9451d97416/access_as_user openid offline_access` |

### Client IDs

| Client | Client ID | Redirect URI |
|--------|-----------|-------------|
| Web (Blazor SPA) | `ab523e40-983c-4f89-adf8-e258d78cb689` | `https://app.moultriemobile.com/authentication/login-callback` |
| Android (MSAL) | `94d66f81-15ef-42c1-a6bc-9e4fc575d075` | `msauth://com.pradco.mmb2c//rn0m6TJIR79gIT+Hb/ZVR1V3+c=` |

### Authorization URL

```
https://login.moultriemobile.com/46148adf-3109-46fc-ac67-9b17d664afc3/oauth2/v2.0/authorize
  ?p=B2C_1A_SIGNUP_SIGNIN
  &client_id=ab523e40-983c-4f89-adf8-e258d78cb689
  &redirect_uri=https://app.moultriemobile.com/authentication/login-callback
  &response_type=code
  &scope=https://moultriemobile.onmicrosoft.com/9e848fa3-9069-4bf0-bcc3-ab9451d97416/access_as_user openid offline_access
  &response_mode=fragment
  &code_challenge=<S256_CHALLENGE>
  &code_challenge_method=S256
  &nonce=<RANDOM_GUID>
  &state=<STATE>
```

### Token Exchange

```
POST https://login.moultriemobile.com/46148adf-3109-46fc-ac67-9b17d664afc3/oauth2/v2.0/token
  ?p=B2C_1A_SIGNUP_SIGNIN

Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&client_id=ab523e40-983c-4f89-adf8-e258d78cb689
&code=<AUTH_CODE>
&redirect_uri=https://app.moultriemobile.com/authentication/login-callback
&code_verifier=<PKCE_VERIFIER>
&scope=https://moultriemobile.onmicrosoft.com/9e848fa3-9069-4bf0-bcc3-ab9451d97416/access_as_user openid offline_access
```

### Token Refresh

```
POST https://login.moultriemobile.com/46148adf-3109-46fc-ac67-9b17d664afc3/oauth2/v2.0/token
  ?p=B2C_1A_SIGNUP_SIGNIN

Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&client_id=ab523e40-983c-4f89-adf8-e258d78cb689
&refresh_token=<REFRESH_TOKEN>
&scope=https://moultriemobile.onmicrosoft.com/9e848fa3-9069-4bf0-bcc3-ab9451d97416/access_as_user openid offline_access
```

### JWT Claims

The access token JWT contains these useful claims:

| Claim | Description | Example |
|-------|-------------|---------|
| `MMId` | Moultrie user ID | `1234567` |
| `email` | User email | (from `.env`) |
| `given_name` | First name | `John` |
| `family_name` | Last name | `Doe` |
| `scp` | Scope | `access_as_user` |
| `azp` | Client ID used | `ab523e40-983c-4f89-adf8-e258d78cb689` |
| `exp` | Expiration (unix) | `1771187758` |

### Token Storage (Web Portal)

- Bearer token: `localStorage` key `MMBlazorBearerToken`
- MSAL access tokens: localStorage keys containing `accesstoken`
- MSAL refresh tokens: localStorage keys containing `refreshtoken`

### Notes

- **No password-based token grant**: ROPC (Resource Owner Password Credentials) flow is **not enabled** on this B2C tenant. Attempting `grant_type=password` against the token endpoint returns `AADB2C90080: The provided grant has expired. Please re-authenticate and try again.` regardless of credentials. This means there is no way to obtain a token with just a username and password via a simple HTTP POST — a browser-based interactive login is required.
- **PKCE is mandatory**: The only supported auth flow is Authorization Code with PKCE. The user must be redirected to the B2C hosted login UI at `login.moultriemobile.com`, enter credentials interactively, and the resulting authorization code is exchanged for tokens via the token endpoint with a `code_verifier`.
- **Automating login** requires a headless browser (Puppeteer, Playwright, etc.) to drive the B2C login page, or intercepting the redirect after manual login to capture the auth code.
- **Token lifetime**: Access tokens expire after ~24 hours. Use the refresh token (returned alongside the access token) to obtain new access tokens without re-authenticating. Refresh tokens have a longer lifetime.
- Both the web client ID and Android client ID produce tokens accepted by both API bases.

---

## Base URLs

| Service | URL |
|---------|-----|
| **Web API** | `https://consumerapi-web-v2.moultriemobile.com` |
| **App API** | `https://consumerapi-app-v2.moultriemobile.com` |
| **Image CDN** | `https://primaryviewer2.moultriemobile.com` |
| **Video CDN** | `https://videos.moultriemobile.com` |
| **Content CDN** | `https://cdncontent.moultriemobile.com` |

Both Web API and App API serve the same endpoints with identical responses. The web portal uses `consumerapi-web-v2`, the Android app uses `consumerapi-app-v2`.

### Required Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
```

---

## Account

### GET /api/v1/Account/AccountDetails

Get the authenticated user's account details, including per-user BLE encryption keys.

**Parameters:**
- `Update` (optional): `false` to skip any account refresh
- `ClientId` (optional): User's MMId (from JWT claims)

**Example:** `GET /api/v1/Account/AccountDetails?Update=false&ClientId=1234567`

**Response:**
```json
{
  "Id": 1234567,
  "Active": true,
  "Address1": "123 Main Street",
  "Address2": null,
  "Banished": false,
  "City": "Springfield",
  "CreatedOn": "2026-01-01T12:00:00.000",
  "FirstName": "John",
  "LastName": "Doe",
  "PrimaryPhone": "5551234567",
  "Role": "user",
  "SecondaryPhone": null,
  "State": "IL",
  "Country": "US",
  "StripeCustomerId": null,
  "ZuoraCustomerId": "<zuora_customer_id>",
  "ZuoraAccountNumber": "<zuora_account_number>",
  "FullName": "John Doe",
  "UserId": 1234567,
  "Username": "user@example.com",
  "Zip": "62704",
  "CompletedSetup": true,
  "HuntingHomeScreen": "gallery",
  "BleKey": "<per-user BLE encryption key, base64>",
  "BleIV": "<per-user BLE IV, base64>",
  "DeclaredCountry": "US",
  "SecurityQuestions": null,
  "SecurityAnswers": null
}
```

> The `BleKey` and `BleIV` fields are per-user encryption keys for BLE camera communication, distinct from the default app-wide BLE keys.

---

## Device / Camera Management

### GET /api/v1/Device/Devices

List all devices on the account.

**Response:**
```json
{
  "Devices": [{
    "DeviceId": 2345678,
    "Model": "EDGE-2-SEC-NW",
    "ModelYear": "2024",
    "FotaEnabled": false,
    "DeviceName": "EDGE 2 Security-9880",
    "LatestActivity": "2026-02-14T20:49:21.14",
    "DeviceBatteryLevel": 97,
    "DeviceSoftwareVersion": "",
    "DeviceAvailableUpdateVersion": null,
    "DeviceAvailableUpdateIsMandatory": false,
    "DeviceSoftwareUpdateAccepted": false,
    "FreeStorageBytes": 7011631104,
    "TotalStorageBytes": 7502299136,
    "CameraSwitchSetting": "C",
    "Status": "Active",
    "DisplayName": "EDGE 2 Security",
    "BatteryDaysRemaining": null,
    "SolarBatteryLevel": null,
    "DeviceType": "camera",
    "MEID": "123456789012345",
    "ModemId": 3456789,
    "ModemType": "EDGE-2-SEC-NW",
    "ModemTypeAllowedPlans": "L",
    "ModemBatteryLevel": 97,
    "SignalStrength": 100,
    "SoftwareVersion": "2.0.24",
    "AvailableUpdateVersion": null,
    "LatestModemActivity": "2026-02-14T20:49:21.14",
    "ModemFotaEnabled": true,
    "CanUploadVideo": true,
    "SoftwareUpdateAccepted": false,
    "IsIntegrated": true,
    "HasPendingSettingsUpdates": false,
    "HasOnDemandSettingsUpdates": false,
    "OnDemandSwitchSetting": true,
    "SetupComplete": true,
    "IsActive": true,
    "SerialNumber": "100000000000001",
    "Location": { "Latitude": null, "Longitude": null },
    "Subscription": {
      "SubscriptionId": 4567890,
      "ActivatedOn": "2026-02-14T16:10:38.83",
      "DowngradePlanName": null,
      "DowngradeEffectiveDate": null,
      "IsUnlimited": true,
      "CycleStartDate": "2026-02-14T00:00:00",
      "CycleEndDate": "2026-03-14T00:00:00",
      "TermEndDate": null,
      "PlanName": "Unlimited",
      "PlanType": "L",
      "EndOnDate": null,
      "TotalImagesAvailable": -1,
      "TotalHiResAvailable": 0,
      "TotalVideosAvailable": 50,
      "TotalHiResUsed": null,
      "TotalVideoUsed": null,
      "TotalImagesUsed": 484,
      "CanUndoCancellation": false,
      "IsPendingCancellation": false
    },
    "DeviceAlerts": [{
      "UserId": 0,
      "Meid": "123456789012345",
      "Title": "",
      "Body": "Subscription is active.",
      "Severity": 0,
      "CreatedOn": "2026-02-14T20:49:22.527+00:00",
      "ExpiresOn": "2026-03-14T00:00:00+00:00",
      "SupportLink": "",
      "DeepLink": "",
      "Category": "Subscription",
      "FeatureFlag": null
    }],
    "AlertBanners": [],
    "SettingsFlags": {
      "HasCameraBattery": true,
      "HasModemBattery": false,
      "HasSDCard": false,
      "HasSignal": true,
      "HasBluetooth": false,
      "HasHealthCheck": false,
      "HasLiveAim": false,
      "HasTimeLapse": true,
      "HasScheduler": true,
      "HasSmartCapture": false,
      "HasExternalPower": true,
      "IsPreinstalled": false,
      "HasRunOnDemand": true,
      "HasGps": false,
      "HasDynamicInstallation": true,
      "IsDeployable": true,
      "MaxFeedSchedules": 0,
      "HasDaysRemaining": false,
      "HasWiredTransfer": false,
      "HasSolarPerformance": false,
      "HasSmartCaptureTargets": false,
      "IsBleHub": false,
      "IsDFC": false,
      "IsHopperBundled": false,
      "HasMinutesTimeFormat": false,
      "HasSmartZones": false,
      "HasInternalPower": false,
      "JsonSupportVersion": null,
      "HasBuckShot": false,
      "HasGen4Ftu": false
    },
    "BatteryVoltageExternal": 0.0,
    "PowerSource": "L",
    "BatteryType": "ALKA",
    "InstallationPath": "/hunting/edge_2/index.json",
    "MacAddress": null,
    "DeviceTypeDescrimintator": "CameraDevice"
  }]
}
```

### GET /api/v1/Device/GetSingleDevice?cameraId={id}

Get detailed info for a single device. Returns same structure as Devices list but for one device.

**Parameters:**
- `cameraId` (required): Device ID (e.g., `2345678`)

### GET /api/v1/Device/GetGroupedSettings?id={cameraId}

Get all configurable camera settings, grouped by category. See [Camera Settings Reference](#camera-settings-reference) for full details.

**Parameters:**
- `id` (required): Camera ID

**Response structure:**
```json
{
  "GroupedSettings": [{
    "Id": "d4e5f6a7-b8c9-0123-defa-234567890123",
    "Title": "General Settings",
    "Name": "general",
    "Order": 1,
    "HasCustomPage": false,
    "Disabled": false,
    "Settings": [{
      "Id": 591,
      "SettingText": "Camera Name",
      "DisplaySettingText": "Camera Name",
      "SettingShortText": "CNM",
      "SettingType": "2",
      "SettingArea": "C",
      "MinLimit": 1,
      "MaxLimit": 20,
      "Value": "EDGE 2 Security-9880",
      "Displayable": true,
      "Editable": true,
      "ModifiedOn": "2026-02-14T17:29:26.887",
      "ToolTip": "Set <b>Camera Name</b> to help you organize...",
      "Order": 1,
      "IsModemSetting": false,
      "Options": [],
      "Alert": null,
      "ParentCameraSettingId": null,
      "HasChildren": false,
      "UserUpdatedOn": "2026-02-14T17:29:26.887",
      "DeviceConfirmedOn": "2026-02-14T20:49:21.147"
    }]
  }]
}
```

**Setting types:**
- `0` = Dropdown (has `Options[]` array with `Value` and `Text`)
- `1` = Toggle (Value is `"T"` for true, `"F"` for false)
- `2` = Text input (has `MinLimit`/`MaxLimit` for length)

**Setting areas:**
- `C` = Camera setting
- `M` = Modem setting

---

## On-Demand Photo & Video

### POST /api/v1/Device/OnDemand

Request an on-demand photo or video from the camera. The camera must have On Demand enabled (`OnDemandSwitchSetting: true`).

**Request:**
```json
{
  "Meid": "123456789012345",
  "DidConsent": true,
  "OnDemandEventType": "image"
}
```

**OnDemandEventType values** (case-insensitive):
- `"image"` / `"IMAGE"` / `"Image"` — Request a photo
- `"video"` / `"VIDEO"` / `"Video"` — Request a video

> Note: `"Photo"`, `"photo"`, `"PHOTO"` do **not** work. Use `"image"` instead.

**Response (200):**
```json
{
  "Success": true,
  "CheckStatusAfterSeconds": 10,
  "ExpectedNextConnection": null
}
```

**Workflow:**
1. Call `POST /api/v1/Device/OnDemand` with type `"image"` or `"video"`
2. Wait `CheckStatusAfterSeconds` seconds (10)
3. Poll `GET /api/v1/Image/GetPendingVideoAndHighResIds?deviceId={id}` to check status
4. When complete, the new image/video appears in `POST /api/v2/Image/ImageSearch` results

---

## Image / Gallery

### POST /api/v2/Image/ImageSearch

Search and paginate through camera images. Note: this is **v2**, not v1.

**Request:**
```json
{
  "PageSize": 20,
  "PageNumber": 1
}
```

**Optional filter fields:**
| Field | Type | Description | Verified |
|-------|------|-------------|----------|
| `CameraId` | int | Filter by camera ID | Yes |
| `StartDate` | string | ISO date start range | Yes |
| `EndDate` | string | ISO date end range | Yes |
| `IsVideo` | bool | Filter video-only | Yes (0 results when no videos) |
| `IsOnDemand` | bool | Filter on-demand images | Accepted (no visible effect if all match) |
| `AlbumId` | int | Filter by album | Accepted but did not filter |
| `IsFavorite` | bool | Filter favorites | Accepted but did not filter |
| `Tags` | array | Filter by tags | Accepted but did not filter |

**Response:**
```json
{
  "Results": {
    "TotalAvailableCount": 379,
    "CurrentPageIndex": 1,
    "CurrentPageSize": 20,
    "FirstPageIndex": 1,
    "LastPageIndex": 19,
    "TotalPages": 19,
    "Results": [{
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "userId": 1234567,
      "cameraId": 2345678,
      "takenOn": "2026-02-14T15:49:04",
      "storedOn": "2026-02-14T20:49:13+00:00",
      "rating": 0,
      "status": "I",
      "fileName": "2345678-20260214204913-100MFCAM_MFDC0440.jpg",
      "localFileName": "100MFCAM_MFDC0440.jpg",
      "type": "H",
      "temperature": "62",
      "moonPhase": "7",
      "pressure": "0",
      "cameraName": "EDGE 2 Security-9880",
      "modemMEID": "123456789012345",
      "imageSize": null,
      "exifData": null,
      "shareId": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "tags": [],
      "flash": true,
      "folder": {
        "Id": 5678901,
        "UserId": 1234567,
        "Name": "EDGE 2 Security-9880"
      },
      "irTags": [],
      "smartCaptureTags": [],
      "imageUrl": "https://primaryviewer2.moultriemobile.com/cloud/images/2345678-20260214204913-100MFCAM_MFDC0440.jpg",
      "enhancedImageUrl": "https://primaryviewer2.moultriemobile.com/cloud/colorizedimages/2345678-20260214204913-100MFCAM_MFDC0440.jpg",
      "isVideo": false,
      "videoOn": null,
      "videoSize": null,
      "videoFile": null,
      "videoUrl": null,
      "forSecurity": false,
      "isTestImage": false,
      "IsOnDemand": true,
      "IsTamper": false,
      "isFavorite": false,
      "downloadUrl": "https://primaryviewer2.moultriemobile.com/cloud/images/2345678-20260214204913-100MFCAM_MFDC0440.jpg",
      "meid": "123456789012345",
      "videoIdentifier": null,
      "latitude": 0.0,
      "longitude": 0.0,
      "isManual": false,
      "CommaSeparatedTags": "None",
      "BurstSequenceId": null,
      "GameProfileIds": [],
      "nativeResolution": "Unknown"
    }]
  }
}
```

**Image type codes:**
- `H` = High resolution
- `T` = Thumbnail

### POST /api/v1/Image/Delete

Delete one or more images.

**Request:**
```json
{
  "Ids": ["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]
}
```

**Response (200):**
```json
{
  "Result": true
}
```

> Internal type: `MM.Core.Consumer.Api.Models.v1.Image.Requests.DeleteImagesParameters`

### POST /api/v1/Image/RequestHighRes

Request high-resolution version of thumbnail images from the camera.

**Request:**
```json
{
  "HiResRequests": [
    {"ImageId": "b2c3d4e5-f6a7-8901-bcde-f12345678901", "CameraId": 2345678}
  ]
}
```

**Response (200):**
```json
{
  "Result": true,
  "Message": "User Requested Hi-Res images for following 1 Meid: 123456789012345 - Image Ids: b2c3d4e5-f6a7-8901-bcde-f12345678901"
}
```

> Internal type: `RequestHighResImagesRequest`. Each item in `HiResRequests` contains `ImageId` (GUID) and `CameraId` (int). Multiple images can be requested in a single call.

**Workflow:**
1. Call this endpoint with image IDs (use type `T` thumbnail images)
2. Poll `GET /api/v1/Image/GetPendingVideoAndHighResIds?deviceId={id}` — pending IDs appear in `PendingHighResIds`
3. When fulfilled, the high-res image URL appears in the image's `imageUrl` field and type changes to `H`

### POST /api/v1/Image/RequestVideo

Request the video clip associated with an image from the camera.

**Request:**
```json
{
  "VideoRequests": [
    {"ImageId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890", "CameraId": 2345678}
  ]
}
```

**Response (200):**
```json
{
  "Result": true,
  "Message": "..."
}
```

> Internal type: `RequestVideoParametersRequest`. Each item in `VideoRequests` contains `ImageId` (GUID) and `CameraId` (int). Camera must be in Photo+Video mode (`CCM` = `V`) for video clips to be available. Returns 500 if the image has no associated video.

**Workflow:**
1. Call this endpoint with image IDs
2. Poll `GET /api/v1/Image/GetPendingVideoAndHighResIds?deviceId={id}` — pending IDs appear in `PendingVideoIds`
3. When fulfilled, the video URL appears in the image's `videoUrl` field (served from `videos.moultriemobile.com`)

### POST /api/v1/Image/GetOdReportingTagsStatus

Check on-demand reporting tag status for images.

**Request:**
```json
{
  "ImageIds": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"]
}
```

**Response:** Returns tag processing status for the given images.

### GET /api/v1/Image/GetPendingVideoAndHighResIds?deviceId={id}

Check status of pending high-res and video requests.

**Parameters:**
- `deviceId` (required): Camera/device ID

**Response:**
```json
{
  "PendingVideoIds": [],
  "PendingHighResIds": []
}
```

### GET /api/v1/Image/Tags

List all user-defined tags.

**Response:**
```json
{
  "Tags": []
}
```

---

## Albums

The Album controller uses a RESTful `/{albumId}` route pattern.

### GET /api/v1/Album

List all albums.

**Response:**
```json
{
  "Albums": [{
    "AlbumId": 1000001,
    "Name": "Favorites",
    "CoverPhoto": null,
    "ModifiedOn": null,
    "IsFavorite": true
  }]
}
```

### POST /api/v1/Album

Create a new album.

**Request:**
```json
{
  "AlbumName": "My New Album"
}
```

**Response (200):**
```json
{
  "AlbumId": 1000002,
  "Name": "My New Album",
  "CoverPhoto": null,
  "ModifiedOn": null,
  "IsFavorite": false
}
```

> Note: `"Favorites"` is a reserved album name and cannot be used.

### POST /api/v1/Album/{albumId}

Edit an album (rename or set cover photo).

**Request:**
```json
{
  "AlbumName": "New Name",
  "CoverPhoto": "https://primaryviewer2.moultriemobile.com/cloud/images/filename.jpg"
}
```

At least one of `AlbumName` or `CoverPhoto` is required. `CoverPhoto` must be an absolute URL.

### POST /api/v1/Album/UpdateImages

Add or remove images from an album. This is also how you toggle favorites (add/remove from the Favorites album).

**Add images to album:**
```json
{
  "AlbumId": 1000001,
  "AddImageIds": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"]
}
```

**Remove images from album:**
```json
{
  "AlbumId": 1000001,
  "RemoveImageIds": ["b2c3d4e5-f6a7-8901-bcde-f12345678901"]
}
```

**Response (200):**
```json
{
  "Success": true,
  "Message": null
}
```

> To toggle favorites: use `AlbumId` of the Favorites album (where `IsFavorite: true` in album list). `AddImageIds` to favorite, `RemoveImageIds` to unfavorite.

### POST /api/v1/Album/EditFavoritesAlbum

Edit the Favorites album metadata (cover photo). Requires a valid absolute URL for `CoverPhoto`.

> Note: Returns 400 if `CoverPhoto` is missing or invalid. This edits the Favorites album itself, not individual image favorite status (use `UpdateImages` for that).

### DELETE /api/v1/Album/{albumId}

Delete an album.

**Response (200):**
```json
{
  "Success": true,
  "Message": null
}
```

---

## Notifications

### GET /api/v1/NotificationCenter/HasUnreadNotification

Check for unread notifications. Works on **app API only** (`consumerapi-app-v2`).

**Response:**
```json
{
  "HasUnreadNotification": false,
  "Success": true,
  "Message": null
}
```

> Note: `GetNotifications` and `GetSettings` routes return 404 on both API bases.

---

## Feature Flags

### GET /api/v1/Feature/{flagName}

Check a feature flag. Returns plain `true` or `false`.

**Enabled flags:**
| Flag | Value |
|------|-------|
| `web-newgallery` | `true` |
| `web-imageimport` | `true` |
| `enhanced` | `true` |
| `hd` | `true` |
| `sharing` | `true` |
| `solar` | `true` |
| `gallery` | `true` |
| `map` | `true` |

**Disabled flags (sampling):**
`on-demand`, `security`, `video`, `burst`, `colorize`, `albums`, `favorites`, `download`, `bulk-download`, `notifications`, `alerts`, `subscription`, `trial`, `battery`, `signal`, `sd-card`, `time-lapse`, `motion-detect`, `photo`, `weather`, `game-plan`, `deer-census`, `smart-tags`, `ir-tags`, `web-on-demand`, `web-security`, `web-video`, `app-on-demand`, `app-security`, `app-video`, `app-deercensus`, `app-deercensus-access`, `app-4kvideoenabled`

---

## Camera Settings Reference

All settings retrieved via `GET /api/v1/Device/GetGroupedSettings?id={cameraId}`.

### General Settings (`general`)

| Setting ID | Short | Name | Type | Current | Options |
|-----------|-------|------|------|---------|---------|
| 591 | CNM | Camera Name | text | `EDGE 2 Security-9880` | 1-20 chars |
| 625 | ODE | On Demand | toggle | `T` (enabled) | T/F |
| 624 | BAT | Power Source | dropdown | `ALKA` | `ALKA` (Alkaline AA), `LITH` (Lithium AA), `CHRG` (Rechargeable Pack) |
| 594 | CTD | Capture Mode | dropdown | `M` | `T` (Time-Lapse), `M` (Motion Detect), `H` (Motion + Time-Lapse) |
| 607 | CCM | Photo or Video | dropdown | `S` | `S` (Photo), `V` (Photo + Video) |
| 5 | MTI | Upload Frequency | dropdown | `3` | `0` (Immediate), `3` (Every 3h), `6` (Every 6h), `12` (Every 12h), `24` (Every 24h) |

### Photo Settings (`photo`)

| Setting ID | Short | Name | Type | Current | Options |
|-----------|-------|------|------|---------|---------|
| 605 | CFF | Motion Freeze | toggle | `F` (off) | T/F |
| 606 | CMS | Multi-Shot | dropdown | `1` | `1` (Single), `3B` (3 Burst), `3T` (3 Trigger) |
| 608 | CCR | Photo Resolution | dropdown | `L` | `E` (Enhanced 33MP), `L` (High 4MP) |

### Video Settings (`video`)

| Setting ID | Short | Name | Type | Current | Options |
|-----------|-------|------|------|---------|---------|
| 619 | CVR | Video Resolution | dropdown | `H` | `L` (HD 720p), `H` (Full HD 1080p) |
| 620 | CVL | Video Length | dropdown | — | (options vary) |

### Motion Detect Settings (`motiondetect`)

| Setting ID | Short | Name | Type | Current | Options |
|-----------|-------|------|------|---------|---------|
| 595 | CPR | PIR Sensitivity | dropdown | — | `L` (Low), `N` (Normal), `H` (High) |
| 596 | CDD | Detection Delay (Photo) | dropdown | — | varies (seconds) |
| 603 | CVD | Detection Delay (Video) | dropdown | — | varies (seconds) |

### POST /api/v1/Device/SaveDeviceSettings

Save individual camera settings by short code. Uses `SettingShortText` to identify which settings to update.

**Request:**
```json
{
  "CameraId": 2345678,
  "Settings": [
    {"SettingShortText": "CNM", "Value": "My Camera Name"},
    {"SettingShortText": "ODE", "Value": "T"}
  ]
}
```

**Response (200):**
```json
{
  "SettingsSaved": true
}
```

> The `Settings` array `Id` field is a GUID (not the integer setting ID from GetGroupedSettings). Use `SettingShortText` instead to identify settings. See [Camera Settings Reference](#camera-settings-reference) for all short codes.

### POST /api/v1/Device/SaveSubgroupedSettings

Save settings organized by group. Uses the group `Name` and integer setting `Id` from GetGroupedSettings.

**Request:**
```json
{
  "CameraId": 2345678,
  "SettingsGroups": [
    {
      "Name": "general",
      "Settings": [
        {"Id": 591, "Value": "My Camera Name"},
        {"Id": 625, "Value": "T"}
      ]
    }
  ]
}
```

**Response (200):**
```json
{
  "SubgroupedSettingsSaved": true
}
```

> Group names: `general`, `photo`, `video`, `motiondetect`. Use this endpoint when saving multiple settings across groups. The integer `Id` comes from the `GetGroupedSettings` response.

---

## Image CDN

Images are served from `primaryviewer2.moultriemobile.com` and are **publicly accessible** (no auth required) if you know the filename.

### URL Patterns

| Type | URL Pattern |
|------|-------------|
| Standard image | `https://primaryviewer2.moultriemobile.com/cloud/images/{filename}` |
| Colorized/enhanced | `https://primaryviewer2.moultriemobile.com/cloud/colorizedimages/{filename}` |
| Video | `https://videos.moultriemobile.com/videos/{userId}/{deviceId}-{uuid}.MP4` |
| Download | Same as standard image URL |

### Filename Format

```
{deviceId}-{storedOnTimestamp}-{localFileName}
```

Example: `2345678-20260214204913-100MFCAM_MFDC0440.jpg`

- `deviceId`: Camera device ID
- `storedOnTimestamp`: UTC timestamp when uploaded (YYYYMMDDHHmmss)
- `localFileName`: Original filename from camera SD card (e.g., `100MFCAM_MFDC0440.jpg`)

---

## Other Services

These subdomains are live but no working API routes were discovered during testing. They likely require different authentication or route prefixes.

| Service | URL | Purpose |
|---------|-----|---------|
| Notifications | `https://notifications.moultriemobile.com/` | Push notification registration |
| Weather | `https://weatherapi.moultriemobile.com` | Weather forecasts for camera location |
| Maps | `https://maps.moultriemobile.com` | Map/pin data |
| Subscriptions | `https://subscriptions.moultriemobile.com` | Plan management |
| Subscriptions Core | `https://subscriptionmanagementapi.moultriemobile.com` | Core subscription API |
| Animal Forecast | `https://animalforecast.dev.moultriemobile.dev/` | Game activity predictions |
| Web Subscription | `https://web.moultriemobile.com/` | Subscription portal (HTML) |
| App Version Check | `https://mmprodappversionchecker.azurewebsites.net/api/AppVersionChecker` | App update check |

### Third-Party Integrations (from app config)

| Service | Key |
|---------|-----|
| Mapbox | `<mapbox_public_key>` |
| OnX Maps OAuth | Client ID: `<onx_client_id>` |
| RevenueCat | `<revenuecat_key>` |
| Firebase | Project: `<firebase_project>`, Number: `<firebase_number>` |
| Sentry | DSN: `<sentry_dsn>` |
| App Insights | Key: `<app_insights_key>` |
| Zuora (Billing) | Client ID: `<zuora_billing_client_id>` |

---

## BLE (Bluetooth) Configuration

For direct camera communication via Bluetooth Low Energy:

| Parameter | Value |
|-----------|-------|
| Default BLE Key | `<base64_ble_key>` |
| Default BLE IV | `<base64_ble_iv>` |
| HMAC Security Key | `<base64_hmac_key>` |
| Buffer Time | 2 seconds |
| Feed Delay | 3 seconds |
| Min Signal for BLE | 4 |

> The app config provides default BLE keys, but each user also has per-user `BleKey` and `BleIV` returned from the `AccountDetails` endpoint. The per-user keys are used for actual camera communication.

---

## Quick Start Example

### 1. Authenticate (get token via browser PKCE flow)

```bash
# After completing browser-based PKCE auth, extract the token:
TOKEN="eyJhbG..."
```

### 2. List cameras

```bash
curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v1/Device/Devices" \
  | python3 -m json.tool
```

### 3. Get camera settings

```bash
curl -s -H "Authorization: Bearer ${TOKEN}" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v1/Device/GetGroupedSettings?id=2345678"
```

### 4. Request on-demand photo

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v1/Device/OnDemand" \
  -d '{"Meid":"123456789012345","DidConsent":true,"OnDemandEventType":"image"}'
```

### 5. Get latest images

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v2/Image/ImageSearch" \
  -d '{"PageSize":10,"PageNumber":1}'
```

### 6. Download an image (no auth needed)

```bash
curl -O "https://primaryviewer2.moultriemobile.com/cloud/images/2345678-20260214204913-100MFCAM_MFDC0440.jpg"
```

### 7. Delete images

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v1/Image/Delete" \
  -d '{"Ids":["a1b2c3d4-e5f6-7890-abcd-ef1234567890"]}'
```

### 8. Create album

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v1/Album" \
  -d '{"AlbumName":"Buck Photos"}'
```

### 9. Save camera settings

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v1/Device/SaveDeviceSettings" \
  -d '{"CameraId":2345678,"Settings":[{"SettingShortText":"CNM","Value":"My Trail Cam"}]}'
```

### 10. Favorite an image

```bash
# Get Favorites album ID from GET /api/v1/Album (look for IsFavorite: true)
curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v1/Album/UpdateImages" \
  -d '{"AlbumId":1000001,"AddImageIds":["b2c3d4e5-f6a7-8901-bcde-f12345678901"]}'
```

### 11. Request high-res image

```bash
curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  "https://consumerapi-web-v2.moultriemobile.com/api/v1/Image/RequestHighRes" \
  -d '{"HiResRequests":[{"ImageId":"b2c3d4e5-f6a7-8901-bcde-f12345678901","CameraId":2345678}]}'
```

---

## Endpoint Summary

| Method | Endpoint | Purpose | Verified |
|--------|----------|---------|----------|
| GET | `/api/v1/Account/AccountDetails` | User profile + BLE keys | Yes |
| GET | `/api/v1/Device/Devices` | List all cameras | Yes |
| GET | `/api/v1/Device/GetSingleDevice?cameraId={id}` | Single camera detail | Yes |
| GET | `/api/v1/Device/GetGroupedSettings?id={id}` | Camera settings | Yes |
| POST | `/api/v1/Device/SaveDeviceSettings` | Save settings (by short code) | Yes |
| POST | `/api/v1/Device/SaveSubgroupedSettings` | Save settings (by group) | Yes |
| POST | `/api/v1/Device/OnDemand` | Request on-demand photo/video | Yes |
| POST | `/api/v2/Image/ImageSearch` | Search/paginate images | Yes |
| POST | `/api/v1/Image/Delete` | Delete images | Yes |
| POST | `/api/v1/Image/RequestHighRes` | Request high-res image | Yes |
| POST | `/api/v1/Image/RequestVideo` | Request video clip | Yes (format confirmed) |
| GET | `/api/v1/Image/GetPendingVideoAndHighResIds?deviceId={id}` | Check pending requests | Yes |
| POST | `/api/v1/Image/GetOdReportingTagsStatus` | OD reporting tag status | Yes |
| GET | `/api/v1/Image/Tags` | List tags | Yes |
| GET | `/api/v1/Album` | List albums | Yes |
| POST | `/api/v1/Album` | Create album | Yes |
| POST | `/api/v1/Album/{id}` | Edit album | Yes |
| POST | `/api/v1/Album/UpdateImages` | Add/remove images from album | Yes |
| POST | `/api/v1/Album/EditFavoritesAlbum` | Edit favorites album metadata | Yes (needs CoverPhoto) |
| DELETE | `/api/v1/Album/{id}` | Delete album | Yes |
| GET | `/api/v1/NotificationCenter/HasUnreadNotification` | Check notifications | Yes (app API) |
| GET | `/api/v1/Feature/{name}` | Feature flag check | Yes |
