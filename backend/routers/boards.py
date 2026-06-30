from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from lib.pinterest import exchange_code, get_auth_url, get_boards, get_pins
from lib.models import PinterestBoard, PinterestPin

router = APIRouter()

_FRONTEND_BASE = "http://localhost:3000"
_CALLBACK_URI = "http://localhost:8000/auth/pinterest/callback"


@router.get("/auth/pinterest")
def pinterest_auth(next: str = Query(default="/setup")):
    """Redirect the user to Pinterest OAuth. Pass ?next=/setup or ?next=/results."""
    url = get_auth_url(redirect_uri=_CALLBACK_URI, next=next)
    return RedirectResponse(url)


@router.get("/auth/pinterest/callback")
async def pinterest_callback(code: str = Query(), state: str = Query()):
    """Pinterest redirects here after the user grants access."""
    try:
        next_path = await exchange_code(code=code, state=state)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(f"{_FRONTEND_BASE}{next_path}")


@router.get("/boards", response_model=list[PinterestBoard])
async def list_boards():
    """Return all Pinterest boards for the authenticated user."""
    try:
        return await get_boards()
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/boards/{board_id}/pins", response_model=list[PinterestPin])
async def list_pins(board_id: str):
    """Return all pins for a given board."""
    try:
        return await get_pins(board_id)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
