from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "backend" / "api" / "bet_intents_api.py"
SETTLER = ROOT / "backend" / "bot" / "v3_settler.py"
ENGINE = ROOT / "backend" / "bot" / "gamification.py"


def test_player_api_routes_are_registered():
    source = API.read_text(encoding="utf-8")

    expected_routes = (
        'app.router.add_get("/api/player/{wallet}",',
        'app.router.add_get("/api/player/{wallet}/quests",',
        'app.router.add_post("/api/player/{wallet}/roulette",',
        'app.router.add_get("/api/leaderboard/weekly",',
        'app.router.add_post("/api/admin/leaderboard/weekly/finalize",',
        'app.router.add_post("/api/admin/player/{wallet}/game-session",',
        'app.router.add_get("/api/admin/raffles",',
        'app.router.add_post("/api/admin/raffles",',
        'app.router.add_get("/api/raffles/active",',
        'app.router.add_post("/api/raffles/{raffle_id}/enter",',
    )
    for route in expected_routes:
        assert route in source


def test_settler_calls_gamification_after_db_settlement():
    source = SETTLER.read_text(encoding="utf-8")

    assert "on_bet_settled as _gamification_on_bet_settled" in source
    assert "apply_settlement_bonuses as _gamification_apply_bonuses" in source
    assert "asyncio.create_task(_gamification_on_bet_settled(" in source
    assert source.index("update_bet_settlement") < source.index(
        "asyncio.create_task(_gamification_on_bet_settled("
    )


def test_gamification_engine_does_not_expose_roulette_weights_to_api():
    api_source = API.read_text(encoding="utf-8")
    engine_source = ENGINE.read_text(encoding="utf-8")

    assert "_ROULETTE_PRIZES" in engine_source
    assert "_ROULETTE_PRIZES" not in api_source
    assert "weight" not in api_source[api_source.find("async def player_roulette") : api_source.find("async def weekly_leaderboard")]


def test_roulette_spend_uses_atomic_rpc_instead_of_select_then_update():
    source = ENGINE.read_text(encoding="utf-8")
    spin_source = source[source.find("async def spin_roulette") : source.find("async def _apply_roulette_prize")]

    assert '"spend_player_roulette_spins"' in source
    assert "await _spend_roulette_spins(wallet, spins)" in spin_source
    assert '.select("roulette_spins,raffle_tokens")' not in spin_source
    assert '"roulette_spins": available - spins' not in spin_source


def test_raffle_entry_uses_atomic_rpc_instead_of_split_token_update():
    api_source = API.read_text(encoding="utf-8")
    raffle_source = api_source[api_source.find("async def raffle_enter") : api_source.find("def create_app")]

    assert 'db.client.rpc("enter_raffle_with_token"' in raffle_source
    assert '.select("raffle_tokens")' not in raffle_source
    assert '"raffle_tokens": tokens - 1' not in raffle_source


def test_gamification_catalog_matches_word_spec_core_quests():
    source = ENGINE.read_text(encoding="utf-8")

    for marker in (
        "ФУТБОЛЬНЫЙ ПАТРИОТ",
        "ИГРОМАН",
        "НАСТОЯЩИЙ ПРИЗМАЧ",
        "РИСКОВЫЙ",
        "ВРЕМЕННЫЙ МИЛЛИОНЕР",
        "МИЛЛИАРДЕР",
        "МАГНАТ",
        "МАЖОР",
        '"football_patriot"',
        '"manual_gameplay"',
        '"outsider_bets"',
        '"outsider_won_prizm"',
        '"won_prizm_threshold"',
    ):
        assert marker in source


def test_level_thresholds_stay_below_prizm_emission_scale():
    source = ENGINE.read_text(encoding="utf-8")

    for marker in (
        '"turnover": 50_000_000',
        '"turnover": 100_000_000',
        '"turnover": 250_000_000',
        '"turnover": 500_000_000',
        '"turnover": 1_000_000_000',
        '"turnover": 2_000_000_000',
        "1_500_000_000",
    ):
        assert marker in source

    for impossible_marker in (
        "10_000_000_000",
        "100_000_000_000",
        "1_000_000_000_000",
        "10_000_000_000_000",
    ):
        assert impossible_marker not in source


def test_gamification_quest_completion_grants_rewards_once():
    source = ENGINE.read_text(encoding="utf-8")

    assert "async def _grant_quest_rewards" in source
    assert "await _grant_quest_rewards(wallet, catalog)" in source
    assert '"reward_claimed" = True' not in source
    assert 'payload["reward_claimed"] = True' in source
    assert '.eq("completed", False)' in source[source.find("async def _write_quest_progress") : source.find("async def _record_settlement_start")]


def test_player_api_exposes_quest_catalog_metadata():
    source = API.read_text(encoding="utf-8")
    enrich_source = source[source.find("def _enrich_quests") : source.find("def _level_progress")]

    assert '"title": catalog.get("title", "")' in enrich_source
    assert '"conditions": catalog.get("conditions", {})' in enrich_source
    assert '"rewards": catalog.get("rewards", [])' in enrich_source


def test_settlement_applies_active_gamification_bonuses_before_payout():
    engine_source = ENGINE.read_text(encoding="utf-8")
    settler_source = SETTLER.read_text(encoding="utf-8")

    assert "async def apply_settlement_bonuses" in engine_source
    assert '"bonus_type") == "pct_win"' in engine_source
    assert '"bonus_type") == "cashback"' in engine_source
    assert ".is_(\"burned_at\", \"null\")" in engine_source
    assert "bonus_result = await _gamification_apply_bonuses(" in settler_source
    assert "settlement_reason = 'CASHBACK_BONUS'" in settler_source


def test_weekly_leaderboard_can_be_finalized_and_prizes_distributed_once():
    engine_source = ENGINE.read_text(encoding="utf-8")
    api_source = API.read_text(encoding="utf-8")

    assert "async def finalize_weekly_leaderboard" in engine_source
    assert "async def _grant_weekly_rank_prize" in engine_source
    assert "await increment_quest_progress(wallet, \"top3\", delta=1.0)" in engine_source
    assert "\"prize_distributed\": True" in engine_source
    assert "async def admin_finalize_weekly_leaderboard" in api_source
    assert "await _gamification_finalize_weekly(week_start=week_start)" in api_source


def test_admin_can_create_exactly_eleven_question_raffles():
    source = API.read_text(encoding="utf-8")

    assert "def _validate_raffle_questions" in source
    assert "len(questions) != 11" in source
    assert "async def admin_raffles" in source
    assert 'db.client.table("raffles").insert(payload)' in source


def test_admin_can_credit_manual_gameplay_sessions_for_gamer_quest():
    source = API.read_text(encoding="utf-8")

    assert "async def admin_credit_game_session" in source
    assert 'await _gamification_increment_quest(wallet, "manual_gameplay", delta=float(sessions))' in source
    assert '"game_session_credited"' in source


def test_express_intent_backend_contract_is_registered():
    source = API.read_text(encoding="utf-8")
    create_source = source[source.find("async def create_intent") : source.find("async def get_intent_status")]

    assert 'bet_type = str(payload.get("bet_type") or "single")' in create_source
    assert 'if bet_type == "express":' in create_source
    assert 'legs_raw = payload.get("legs") or []' in create_source
    assert 'len(legs_raw) < 2' in create_source
    assert 'len(legs_raw) > 12' in create_source
    assert '"DUPLICATE_MATCH_IN_EXPRESS"' in create_source
    assert 'if combined_odds > 100.0:' in create_source
    assert 'combined_odds = 100.0' in create_source
    assert 'bet_type="express"' in create_source
    assert 'express_legs=normalized_legs' in create_source


def test_express_settler_uses_all_legs_before_settlement():
    source = SETTLER.read_text(encoding="utf-8")
    express_source = source[source.find("# ---------- EXPRESS settlement ----------") : source.find("# ---------- SINGLE settlement ----------")]

    assert "bet_type == 'express'" in express_source
    assert "intent.get('express_legs')" in express_source
    assert "for leg in legs:" in express_source
    assert "incomplete = True" in express_source
    assert "base_payout = round(amount * odds_fixed, 2) if verdict else 0.0" in express_source
    assert "bonus_result = await _gamification_apply_bonuses(" in express_source
    assert "status = 'won' if verdict or payout_amount > 0 else 'lost'" in express_source
    assert "'bonus_result': bonus_result" in express_source
