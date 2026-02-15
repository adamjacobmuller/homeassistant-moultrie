"""Constants for the Moultrie Mobile integration."""

from homeassistant.const import Platform

DOMAIN = "moultrie"

# Azure AD B2C constants
B2C_HOST = "https://login.moultriemobile.com"
TENANT_ID = "46148adf-3109-46fc-ac67-9b17d664afc3"
CLIENT_ID = "ab523e40-983c-4f89-adf8-e258d78cb689"
POLICY = "B2C_1A_SIGNUP_SIGNIN"
REDIRECT_URI = "https://app.moultriemobile.com/authentication/login-callback"
SCOPE = (
    "https://moultriemobile.onmicrosoft.com/"
    "9e848fa3-9069-4bf0-bcc3-ab9451d97416/access_as_user openid offline_access"
)
TOKEN_URL = f"{B2C_HOST}/{TENANT_ID}/oauth2/v2.0/token?p={POLICY}"

# API base
API_BASE = "https://consumerapi-web-v2.moultriemobile.com"
IMAGE_CDN = "https://primaryviewer2.moultriemobile.com"

# Config keys
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"

# Update interval in minutes
UPDATE_INTERVAL = 5

# Platforms
PLATFORMS: list[Platform] = [
    Platform.CAMERA,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.SELECT,
    Platform.BUTTON,
]
