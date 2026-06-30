import json
import logging
import time
from unittest.mock import patch

import pytest
import respx
from httpx import Response

import lib.pinterest as pinterest_module
from lib.pinterest import (
    _TOKEN_URL,
    _BASE_URL,
    exchange_code,
    get_auth_url,
    get_boards,
    get_pins,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_oauth_state():
    """Reset in-memory OAuth state before each test."""
    pinterest_module._oauth_state.clear()
    yield
    pinterest_module._oauth_state.clear()


@pytest.fixture(autouse=True)
def patch_env(monkeypatch):
    monkeypatch.setenv("PINTEREST_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("PINTEREST_CLIENT_SECRET", "test-client-secret")


def _valid_token(expired: bool = False) -> dict:
    return {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "expires_at": time.time() + (-100 if expired else 3600),
    }


# ── OAuth URL ─────────────────────────────────────────────────────────────────

def test_get_auth_url_contains_required_params():
    url = get_auth_url(redirect_uri="http://localhost:8000/auth/pinterest/callback")
    assert "client_id=test-client-id" in url
    assert "response_type=code" in url
    assert "code_challenge_method=S256" in url
    assert "state=" in url


def test_get_auth_url_stores_next_path():
    get_auth_url(redirect_uri="http://localhost:8000/callback", next="/results")
    assert pinterest_module._oauth_state["next"] == "/results"


# ── exchange_code ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_exchange_code_saves_token_and_returns_next(tmp_path, monkeypatch):
    monkeypatch.setattr(pinterest_module, "_TOKEN_PATH", tmp_path / "token.json")

    # Prime OAuth state as if get_auth_url was called
    pinterest_module._oauth_state.update({
        "state": "valid-state",
        "verifier": "test-verifier",
        "redirect_uri": "http://localhost:8000/callback",
        "next": "/setup",
    })

    respx.post(_TOKEN_URL).mock(return_value=Response(200, json={
        "access_token": "new-token",
        "refresh_token": "new-refresh",
        "expires_in": 3600,
    }))

    next_path = await exchange_code(code="auth-code", state="valid-state")

    assert next_path == "/setup"
    saved = json.loads((tmp_path / "token.json").read_text())
    assert saved["access_token"] == "new-token"


@pytest.mark.asyncio
async def test_exchange_code_raises_on_state_mismatch():
    pinterest_module._oauth_state["state"] = "correct-state"
    with pytest.raises(ValueError, match="state mismatch"):
        await exchange_code(code="code", state="wrong-state")


def test_token_value_never_logged(tmp_path, monkeypatch, caplog):
    """The raw access token must not appear in log output."""
    monkeypatch.setattr(pinterest_module, "_TOKEN_PATH", tmp_path / "token.json")
    token = _valid_token()
    (tmp_path / "token.json").write_text(json.dumps(token))

    with caplog.at_level(logging.DEBUG, logger="lib.pinterest"):
        pinterest_module._load_token()

    assert token["access_token"] not in caplog.text


# ── get_boards ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_get_boards_returns_board_list(tmp_path, monkeypatch):
    monkeypatch.setattr(pinterest_module, "_TOKEN_PATH", tmp_path / "token.json")
    (tmp_path / "token.json").write_text(json.dumps(_valid_token()))

    respx.get(f"{_BASE_URL}/boards").mock(return_value=Response(200, json={
        "items": [
            {"id": "board-1", "name": "Autumn Fits", "media": {"image_cover_url": "http://img/1.jpg"}},
            {"id": "board-2", "name": "Minimal", "media": {}},
        ],
        "bookmark": None,
    }))

    boards = await get_boards()

    assert len(boards) == 2
    assert boards[0].id == "board-1"
    assert boards[0].name == "Autumn Fits"
    assert boards[0].thumbnail_url == "http://img/1.jpg"
    assert boards[1].thumbnail_url is None


@pytest.mark.asyncio
@respx.mock
async def test_get_boards_follows_pagination(tmp_path, monkeypatch):
    monkeypatch.setattr(pinterest_module, "_TOKEN_PATH", tmp_path / "token.json")
    (tmp_path / "token.json").write_text(json.dumps(_valid_token()))

    call_count = 0

    def paginated_response(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return Response(200, json={
                "items": [{"id": "b1", "name": "Page 1", "media": {}}],
                "bookmark": "cursor-abc",
            })
        return Response(200, json={
            "items": [{"id": "b2", "name": "Page 2", "media": {}}],
            "bookmark": None,
        })

    respx.get(f"{_BASE_URL}/boards").mock(side_effect=paginated_response)

    boards = await get_boards()
    assert len(boards) == 2
    assert call_count == 2


# ── get_pins ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_get_pins_returns_pin_list(tmp_path, monkeypatch):
    monkeypatch.setattr(pinterest_module, "_TOKEN_PATH", tmp_path / "token.json")
    (tmp_path / "token.json").write_text(json.dumps(_valid_token()))

    respx.get(f"{_BASE_URL}/boards/board-1/pins").mock(return_value=Response(200, json={
        "items": [
            {
                "id": "pin-1",
                "title": "Nice coat",
                "description": "brown wool",
                "link": "http://example.com",
                "media": {"images": {"original": {"url": "http://img/pin1.jpg"}}},
            },
        ],
        "bookmark": None,
    }))

    pins = await get_pins("board-1")

    assert len(pins) == 1
    assert pins[0].id == "pin-1"
    assert pins[0].image_url == "http://img/pin1.jpg"
    assert pins[0].title == "Nice coat"


@pytest.mark.asyncio
@respx.mock
async def test_get_pins_skips_pins_without_images(tmp_path, monkeypatch):
    monkeypatch.setattr(pinterest_module, "_TOKEN_PATH", tmp_path / "token.json")
    (tmp_path / "token.json").write_text(json.dumps(_valid_token()))

    respx.get(f"{_BASE_URL}/boards/board-1/pins").mock(return_value=Response(200, json={
        "items": [
            {"id": "pin-no-img", "media": {}, "title": None, "description": None, "link": None},
        ],
        "bookmark": None,
    }))

    pins = await get_pins("board-1")
    assert pins == []


# ── Token refresh ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_expired_token_triggers_refresh(tmp_path, monkeypatch):
    monkeypatch.setattr(pinterest_module, "_TOKEN_PATH", tmp_path / "token.json")
    (tmp_path / "token.json").write_text(json.dumps(_valid_token(expired=True)))

    respx.post(_TOKEN_URL).mock(return_value=Response(200, json={
        "access_token": "refreshed-token",
        "expires_in": 3600,
    }))
    respx.get(f"{_BASE_URL}/boards").mock(return_value=Response(200, json={
        "items": [], "bookmark": None,
    }))

    await get_boards()

    saved = json.loads((tmp_path / "token.json").read_text())
    assert saved["access_token"] == "refreshed-token"
