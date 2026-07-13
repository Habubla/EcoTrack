"""easy-auth.dev integration for EcoTrack."""
from __future__ import annotations

import requests

EASY_AUTH_BASE = "https://easy-auth.dev"
_OWNER = "nishchay"
_PROJECT = "ecotrack"
_API_ROOT = f"{EASY_AUTH_BASE}/api/auth/{_OWNER}/{_PROJECT}"


def login(username: str, password: str) -> tuple[bool, str, dict]:
    """Authenticate against easy-auth.dev.

    Returns (success, message, payload).
    payload contains 'token' and 'user' on success.
    """
    try:
        resp = requests.post(
            f"{_API_ROOT}/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        data = _safe_json(resp)

        if resp.status_code == 200:
            return True, "Login successful.", data

        msg = data.get("message") or data.get("error") or f"Login failed ({resp.status_code})."
        return False, msg, {}

    except requests.exceptions.ConnectionError:
        return False, "Cannot reach easy-auth.dev — check your internet connection.", {}
    except requests.exceptions.Timeout:
        return False, "easy-auth.dev timed out. Try again.", {}
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}", {}


def register(username: str, email: str, password: str) -> tuple[bool, str, dict]:
    """Create a new account on easy-auth.dev.

    Returns (success, message, payload).
    """
    try:
        resp = requests.post(
            f"{_API_ROOT}/register",
            json={"username": username, "email": email, "password": password},
            timeout=10,
        )
        data = _safe_json(resp)

        if resp.status_code in (200, 201):
            return True, "Account created successfully.", data

        msg = data.get("message") or data.get("error") or f"Registration failed ({resp.status_code})."
        return False, msg, {}

    except requests.exceptions.ConnectionError:
        return False, "Cannot reach easy-auth.dev — check your internet connection.", {}
    except requests.exceptions.Timeout:
        return False, "easy-auth.dev timed out. Try again.", {}
    except Exception as exc:  # noqa: BLE001
        return False, f"Unexpected error: {exc}", {}


def _safe_json(resp: requests.Response) -> dict:
    try:
        return resp.json()
    except Exception:  # noqa: BLE001
        return {}
