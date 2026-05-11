from datetime import datetime

from backend.api.bet_intents_api import _build_match_snapshot
from backend.bot.v3_settler import _merge_match, _single_intent_snapshot
from backend.score_enricher import _parse_match_date, _snapshot_to_match_item


def test_single_coupon_snapshot_preserves_match_identity_and_line():
    snapshot = _build_match_snapshot(
        {
            "id": "leon_123",
            "team1": "Home FC",
            "team2": "Away FC",
            "league": "Test League",
            "sport": "football",
            "match_time": "2026-05-10T15:00:00+03:00",
            "p1": "2.13",
            "source": "Leonbets",
        },
        outcome="P1",
        odds=2.13,
    )

    assert snapshot["match_id"] == "leon_123"
    assert snapshot["team1"] == "Home FC"
    assert snapshot["team2"] == "Away FC"
    assert snapshot["outcome"] == "P1"
    assert snapshot["odds"] == 2.13


def test_settler_can_resolve_single_snapshot_from_existing_json_column():
    intent = {
        "match_id": "leon_123",
        "bet_type": "single",
        "express_legs": [
            {
                "match_id": "leon_123",
                "team1": "Home FC",
                "team2": "Away FC",
                "score": "2:1",
            }
        ],
    }

    assert _single_intent_snapshot(intent, "leon_123")["score"] == "2:1"


def test_settler_keeps_snapshot_score_when_current_match_has_no_score():
    merged = _merge_match(
        {"id": "leon_123", "team1": "Home FC", "score": ""},
        {"id": "leon_123", "team1": "Home FC", "score": "2:1"},
    )

    assert merged["score"] == "2:1"


def test_score_enricher_can_rehydrate_pending_snapshot_as_match_item():
    item = _snapshot_to_match_item(
        {
            "match_id": "leon_123",
            "team1": "Home FC",
            "team2": "Away FC",
            "match_time": "2026-05-10T15:00:00+03:00",
        }
    )

    assert item["id"] == "leon_123"
    assert item["team1"] == "Home FC"
    assert item["team2"] == "Away FC"
    assert _parse_match_date(item) == datetime.fromisoformat("2026-05-10T15:00:00+03:00")
