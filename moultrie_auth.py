#!/usr/bin/env python3
"""
Moultrie Mobile API authentication via Azure AD B2C PKCE flow.

Performs the full OAuth2 Authorization Code + PKCE flow using raw HTTP
requests against the B2C login endpoints (no browser emulation needed).

Outputs:
  - .token       — Bearer access token
  - .refresh     — Refresh token
  - .token_json  — Full token response JSON

Usage:
  python3 moultrie_auth.py                    # Initial login
  python3 moultrie_auth.py --refresh          # Refresh using saved .refresh token
  python3 moultrie_auth.py --refresh TOKEN    # Refresh using provided token
"""

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import sys
import urllib.parse
from pathlib import Path

import requests

TENANT_ID = "46148adf-3109-46fc-ac67-9b17d664afc3"
CLIENT_ID = "ab523e40-983c-4f89-adf8-e258d78cb689"
POLICY = "B2C_1A_SIGNUP_SIGNIN"
REDIRECT_URI = "https://app.moultriemobile.com/authentication/login-callback"
SCOPE = "https://moultriemobile.onmicrosoft.com/9e848fa3-9069-4bf0-bcc3-ab9451d97416/access_as_user openid offline_access"
B2C_HOST = "https://login.moultriemobile.com"
TOKEN_URL = f"{B2C_HOST}/{TENANT_ID}/oauth2/v2.0/token?p={POLICY}"

SCRIPT_DIR = Path(__file__).parent


def generate_pkce():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def login(email: str, password: str) -> dict:
    """Perform full PKCE login and return token response dict."""
    verifier, challenge = generate_pkce()
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)

    session = requests.Session()

    # Step 1: GET authorize page to obtain CSRF token and transaction ID
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
        print("ERROR: Could not find SETTINGS on login page", file=sys.stderr)
        sys.exit(1)

    settings = json.loads(settings_match.group(1))
    csrf = settings["csrf"]
    trans_id = settings["transId"]
    policy_path = settings["hosts"]["policy"]

    # Step 2: POST credentials to SelfAsserted endpoint
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
        print(f"ERROR: Login failed: {sa_result}", file=sys.stderr)
        sys.exit(1)

    # Step 3: Follow confirmed redirect to get authorization code
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
        print(f"ERROR: Expected redirect, got {resp.status_code}", file=sys.stderr)
        sys.exit(1)

    location = resp.headers["Location"]
    frag_params = urllib.parse.parse_qs(urllib.parse.urlparse(location).fragment)
    if "code" not in frag_params:
        print(f"ERROR: No auth code in redirect: {location[:200]}", file=sys.stderr)
        sys.exit(1)
    code = frag_params["code"][0]

    # Step 4: Exchange authorization code for tokens
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
    return resp.json()


def refresh(refresh_token: str) -> dict:
    """Use a refresh token to get new access + refresh tokens."""
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "refresh_token": refresh_token,
            "scope": SCOPE,
        },
    )
    resp.raise_for_status()
    return resp.json()


def save_tokens(tokens: dict):
    """Save tokens to files in the script directory."""
    token_path = SCRIPT_DIR / ".token"
    refresh_path = SCRIPT_DIR / ".refresh"
    json_path = SCRIPT_DIR / ".token_json"

    token_path.write_text(tokens["access_token"])
    refresh_path.write_text(tokens["refresh_token"])
    json_path.write_text(json.dumps(tokens, indent=2))

    # Decode and show expiry info
    try:
        payload = tokens["access_token"].split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.b64decode(payload))
        import datetime
        exp = datetime.datetime.fromtimestamp(claims["exp"])
        print(f"  User:    {claims.get('email', 'unknown')}")
        print(f"  MMId:    {claims.get('MMId', 'unknown')}")
        print(f"  Expires: {exp.isoformat()}")
    except Exception:
        pass

    print(f"\nSaved:")
    print(f"  {token_path}      — access token ({len(tokens['access_token'])} chars)")
    print(f"  {refresh_path}    — refresh token ({len(tokens['refresh_token'])} chars)")
    print(f"  {json_path} — full response")


def main():
    parser = argparse.ArgumentParser(description="Moultrie Mobile API authentication")
    parser.add_argument(
        "--refresh",
        nargs="?",
        const="__file__",
        metavar="TOKEN",
        help="Refresh tokens instead of full login. Optionally provide the refresh token directly.",
    )
    default_email = os.environ.get("MOULTRIE_EMAIL", "")
    default_password = os.environ.get("MOULTRIE_PASSWORD", "")
    parser.add_argument("--email", default=default_email)
    parser.add_argument("--password", default=default_password)
    args = parser.parse_args()

    if args.refresh is not None:
        if args.refresh == "__file__":
            refresh_path = SCRIPT_DIR / ".refresh"
            if not refresh_path.exists():
                print("ERROR: No .refresh file found. Run without --refresh first.", file=sys.stderr)
                sys.exit(1)
            rt = refresh_path.read_text().strip()
        else:
            rt = args.refresh

        print("Refreshing tokens...")
        tokens = refresh(rt)
    else:
        print("Logging in...")
        tokens = login(args.email, args.password)

    save_tokens(tokens)
    print("\nDone.")


if __name__ == "__main__":
    main()
