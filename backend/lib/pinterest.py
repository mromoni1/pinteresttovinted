import hashlib
import json
import logging
import os
import secrets
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv

from lib.models import PinterestBoard, PinterestPin

load_dotenv()

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.pinterest.com/v5"
_AUTH_URL = "https://www.pinterest.com/oauth/"
_TOKEN_URL = "https://api.pinterest.com/v5/oauth/token"
_TOKEN_PATH = Path.home() / ".stylematch" / "pinterest_token.json"
_SCOPES = "boards:read,pins:read"

# PKCE state stored in memory for the duration of the OAuth flow
_oauth_state: dict = {}


def _client_id() -> str:
    val = os.getenv("PINTEREST_CLIENT_ID")
    if not val:
        raise RuntimeError("PINTEREST_CLIENT_ID not set")
    return val


def _client_secret() -> str:
    val = os.getenv("PINTEREST_CLIENT_SECRET")
    if not val:
        raise RuntimeError("PINTEREST_CLIENT_SECRET not set")
    return val


def _save_token(token: dict) -> None:
    _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    _TOKEN_PATH.write_text(json.dumps(token))
    logger.info("Pinterest token saved")


def _load_token() -> dict | None:
    if not _TOKEN_PATH.exists():
        return None
    return json.loads(_TOKEN_PATH.read_text())


def _token_is_expired(token: dict) -> bool:
    expires_at = token.get("expires_at", 0)
    return time.time() >= expires_at - 60  # 60s buffer


async def _refresh_token() -> dict:
    token = _load_token()
    if not token or not token.get("refresh_token"):
        raise RuntimeError("No refresh token available — re-authenticate via /auth/pinterest")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
            },
            auth=(_client_id(), _client_secret()),
        )
        resp.raise_for_status()

    new_token = resp.json()
    new_token["expires_at"] = time.time() + new_token.get("expires_in", 3600)
    new_token.setdefault("refresh_token", token["refresh_token"])
    _save_token(new_token)
    logger.info("Pinterest token refreshed")
    return new_token


async def _get_access_token() -> str:
    token = _load_token()
    if token is None:
        raise RuntimeError("Not authenticated — complete Pinterest OAuth first")
    if _token_is_expired(token):
        token = await _refresh_token()
    return token["access_token"]


def get_auth_url(redirect_uri: str, next: str = "/setup") -> str:
    """Return the Pinterest OAuth URL. Caller should redirect the user there."""
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = (
        hashlib.sha256(verifier.encode()).digest().hex()
    )
    _oauth_state["state"] = state
    _oauth_state["verifier"] = verifier
    _oauth_state["redirect_uri"] = redirect_uri
    _oauth_state["next"] = next

    params = {
        "client_id": _client_id(),
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": _SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str, state: str) -> str:
    """Exchange the authorization code for a token, save it locally, return the next path."""
    if state != _oauth_state.get("state"):
        raise ValueError("OAuth state mismatch — possible CSRF")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            _TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": _oauth_state["redirect_uri"],
                "code_verifier": _oauth_state["verifier"],
            },
            auth=(_client_id(), _client_secret()),
        )
        resp.raise_for_status()

    token = resp.json()
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    _save_token(token)
    next_path = _oauth_state.get("next", "/setup")
    _oauth_state.clear()
    return next_path


async def get_boards() -> list[PinterestBoard]:
    """Return all boards for the authenticated user."""
    access_token = await _get_access_token()
    boards: list[PinterestBoard] = []
    bookmark: str | None = None

    async with httpx.AsyncClient() as client:
        while True:
            params: dict = {"page_size": 25}
            if bookmark:
                params["bookmark"] = bookmark

            resp = await client.get(
                f"{_BASE_URL}/boards",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                boards.append(PinterestBoard(
                    id=item["id"],
                    name=item["name"],
                    thumbnail_url=item.get("media", {}).get("image_cover_url"),
                ))

            bookmark = data.get("bookmark")
            if not bookmark:
                break

    return boards


async def get_pins(board_id: str) -> list[PinterestPin]:
    """Return all pins for the given board, following pagination."""
    access_token = await _get_access_token()
    pins: list[PinterestPin] = []
    bookmark: str | None = None

    async with httpx.AsyncClient() as client:
        while True:
            params: dict = {"page_size": 25}
            if bookmark:
                params["bookmark"] = bookmark

            resp = await client.get(
                f"{_BASE_URL}/boards/{board_id}/pins",
                params=params,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                image_url = _extract_image_url(item)
                if not image_url:
                    continue
                pins.append(PinterestPin(
                    id=item["id"],
                    image_url=image_url,
                    title=item.get("title") or None,
                    description=item.get("description") or None,
                    link=item.get("link") or None,
                ))

            bookmark = data.get("bookmark")
            if not bookmark:
                break

    return pins


def _extract_image_url(pin: dict) -> str | None:
    """Pull the largest available image URL from a pin's media field."""
    images = pin.get("media", {}).get("images", {})
    if not images:
        return None
    # Prefer larger sizes; Pinterest returns keys like "original", "1200x", "600x", "400x200", "150x150"
    for size in ("original", "1200x", "600x", "400x200", "150x150"):
        if size in images:
            return images[size].get("url")
    # Fall back to whatever is available
    first = next(iter(images.values()), {})
    return first.get("url")
