import pytest

from lib.supabase import get_client


@pytest.fixture
def db():
    return get_client()


async def test_insert_and_fetch_style_profile(db):
    profile_row = db.table("style_profiles").insert({
        "board_ids": ["board_123"],
        "anchor_pin_urls": ["https://pinterest.com/pin/1"],
    }).execute()

    profile_id = profile_row.data[0]["id"]

    try:
        db.table("style_features").insert({
            "style_profile_id": profile_id,
            "label": "muted earth tones",
            "confidence": 0.9,
            "examples": ["https://pinterest.com/pin/1"],
        }).execute()

        fetched = (
            db.table("style_profiles")
            .select("*, style_features(*)")
            .eq("id", profile_id)
            .single()
            .execute()
        )

        assert fetched.data["id"] == profile_id
        assert fetched.data["board_ids"] == ["board_123"]
        assert len(fetched.data["style_features"]) == 1
        assert fetched.data["style_features"][0]["label"] == "muted earth tones"
    finally:
        db.table("style_profiles").delete().eq("id", profile_id).execute()
