#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Automatic settlement loop for intent-based v3 bets."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from backend.bot.gamification import (
    apply_settlement_bonuses as _gamification_apply_bonuses,
    on_bet_settled as _gamification_on_bet_settled,
)
from backend.db.supabase_client import db
from backend.utils.bet_views import load_matches_cache, normalize_outcome_label
from backend.utils.operator_audit import log_operator_event
from backend.utils.operator_alerts import notify_bet_settled

POLL_INTERVAL_SECONDS = 180
SETTLEMENT_FETCH_LIMIT = 400

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)


async def _ensure_db() -> None:
    if not db.initialized:
        db.init()
    if not db.initialized:
        raise RuntimeError('Supabase is not configured')


def _parse_score(score: Any) -> tuple[int, int] | None:
    text = str(score or '').strip()
    if not text:
        return None
    numbers = re.findall(r'\d+', text)
    if len(numbers) < 2:
        return None
    try:
        return int(numbers[0]), int(numbers[1])
    except Exception:
        return None


def _parse_total_market(outcome: Any) -> tuple[str, float] | None:
    raw = str(outcome or '').strip().upper().replace(',', '.')
    if not raw:
        return None

    prefixes = {
        'ТБ': 'over',
        'TB': 'over',
        'OVER': 'over',
        'ТМ': 'under',
        'TM': 'under',
        'UNDER': 'under',
    }
    for prefix, tone in prefixes.items():
        if raw.startswith(prefix):
            tail = raw[len(prefix):].strip(' _-')
            match = re.search(r'(\d+(?:\.\d+)?)', tail)
            if not match:
                return None
            value = float(match.group(1))
            if value > 2.5:
                return None
            return tone, value
    return None


def determine_bet_result(outcome: Any, home_goals: int, away_goals: int) -> bool | None:
    label = normalize_outcome_label(outcome)
    if label == 'П1':
        return home_goals > away_goals
    if label == 'X':
        return home_goals == away_goals
    if label == 'П2':
        return away_goals > home_goals
    if label == '1X':
        return home_goals >= away_goals
    if label == '12':
        return home_goals != away_goals
    if label == 'X2':
        return away_goals >= home_goals

    total_market = _parse_total_market(outcome)
    if total_market:
        tone, value = total_market
        total = home_goals + away_goals
        return total > value if tone == 'over' else total < value

    return None


async def run_once(limit: int = SETTLEMENT_FETCH_LIMIT) -> int:
    await _ensure_db()
    bets = await db.get_bets_by_status(['accepted'], limit=limit)
    if not bets:
        return 0

    intent_map = await db.get_bet_intents_map([str(item.get('intent_hash') or '') for item in bets])

    # Collect all match_ids: single bets + every express leg
    match_ids: list[str] = []
    for bet in bets:
        intent = intent_map.get(str(bet.get('intent_hash') or '').upper()) or {}
        match_id = str(bet.get('match_id') or intent.get('match_id') or '').strip()
        if match_id:
            match_ids.append(match_id)
        legs = intent.get('express_legs') or []
        if isinstance(legs, list):
            for leg in legs:
                if isinstance(leg, dict):
                    leg_mid = str(leg.get('match_id') or '').strip()
                    if leg_mid:
                        match_ids.append(leg_mid)
    match_map = await db.get_matches_map(match_ids)
    match_cache = load_matches_cache()

    def _resolve_match(mid: str) -> dict:
        return match_map.get(mid) or match_cache.get(mid) or {}

    settled = 0
    for bet in bets:
        intent_hash = str(bet.get('intent_hash') or '').strip().upper()
        intent = intent_map.get(intent_hash) or {}
        match_id = str(bet.get('match_id') or intent.get('match_id') or '').strip()
        match = _resolve_match(match_id)

        bet_type = str(intent.get('bet_type') or 'single').strip().lower()

        # ---------- EXPRESS settlement ----------
        if bet_type == 'express':
            legs = intent.get('express_legs') or []
            if not isinstance(legs, list) or not legs:
                log.warning('[EXPRESS] tx=%s has no legs in intent', str(bet.get('tx_id') or '')[:18])
                continue

            verdict: bool | None = True
            incomplete = False
            unsupported = False
            for leg in legs:
                if not isinstance(leg, dict):
                    unsupported = True
                    break
                leg_mid = str(leg.get('match_id') or '').strip()
                leg_outcome = leg.get('outcome')
                leg_match = _resolve_match(leg_mid)
                leg_score = _parse_score(leg_match.get('score'))
                if not leg_score:
                    incomplete = True
                    break
                leg_verdict = determine_bet_result(leg_outcome, leg_score[0], leg_score[1])
                if leg_verdict is None:
                    unsupported = True
                    break
                if not leg_verdict:
                    verdict = False
                    break  # one leg lost → express lost; remaining legs irrelevant

            if unsupported:
                log.warning('[EXPRESS] unsupported market tx=%s', str(bet.get('tx_id') or '')[:18])
                continue
            if incomplete:
                continue  # wait for all legs to finish

            odds_fixed = float(bet.get('odds_fixed') or intent.get('odds_fixed') or 0)
            amount = float(bet.get('amount_prizm') or 0)
            base_payout = round(amount * odds_fixed, 2) if verdict else 0.0
            sender_wallet = str(bet.get('sender_wallet') or intent.get('sender_wallet') or '').strip().upper()
            bonus_result = await _gamification_apply_bonuses(
                wallet=sender_wallet,
                bet_tx_id=str(bet.get('tx_id') or ''),
                amount_prizm=amount,
                base_payout=base_payout,
                won=verdict,
            )
            payout_amount = float(bonus_result.get('payout_amount') or base_payout)
            status = 'won' if verdict or payout_amount > 0 else 'lost'
            settlement_reason = 'CASHBACK_BONUS' if (not verdict and payout_amount > 0) else None
            updated_rows = await db.update_bet_settlement(
                str(bet.get('tx_id') or ''),
                status=status,
                payout_amount=payout_amount,
                reason=settlement_reason,
            )
            updated = updated_rows[0] if updated_rows else {**bet, 'status': status, 'payout_amount': payout_amount}
            await log_operator_event(
                'bet_won' if verdict else 'bet_lost',
                updated,
                intent=dict(intent) if intent else None,
                match=dict(match) if match else None,
                extra={'bet_type': 'express', 'legs_count': len(legs), 'bonus_result': bonus_result},
            )
            await notify_bet_settled(updated, intent=dict(intent) if intent else None, match=dict(match) if match else None)

            try:
                if sender_wallet:
                    asyncio.create_task(_gamification_on_bet_settled(
                        wallet=sender_wallet,
                        bet_tx_id=str(bet.get('tx_id') or ''),
                        amount_prizm=float(bet.get('amount_prizm') or 0),
                        odds=odds_fixed,
                        won=verdict,
                        league=str((legs[0] or {}).get('league') or match.get('league') or ''),
                        sport=str((legs[0] or {}).get('sport') or match.get('sport') or ''),
                    ))
            except Exception as _gex:
                log.warning('[GAMIFICATION] express hook error tx=%s: %s', str(bet.get('tx_id') or '')[:18], _gex)

            settled += 1
            log.info('[SETTLED-EXPRESS] tx=%s status=%s legs=%s', str(bet.get('tx_id') or '')[:18], status, len(legs))
            continue

        # ---------- SINGLE settlement ----------
        score_pair = _parse_score(match.get('score'))
        if not score_pair:
            continue

        outcome = intent.get('outcome') or bet.get('outcome')
        verdict = determine_bet_result(outcome, score_pair[0], score_pair[1])
        if verdict is None:
            log.warning('Unsupported market for settlement: tx=%s outcome=%s', bet.get('tx_id'), outcome)
            continue

        odds_fixed = float(bet.get('odds_fixed') or intent.get('odds_fixed') or 0)
        amount = float(bet.get('amount_prizm') or 0)
        base_payout = round(amount * odds_fixed, 2) if verdict else 0.0
        sender_wallet = str(
            bet.get('sender_wallet') or intent.get('sender_wallet') or ''
        ).strip().upper()
        bonus_result = await _gamification_apply_bonuses(
            wallet=sender_wallet,
            bet_tx_id=str(bet.get('tx_id') or ''),
            amount_prizm=amount,
            base_payout=base_payout,
            won=verdict,
        )
        payout_amount = float(bonus_result.get('payout_amount') or base_payout)
        status = 'won' if verdict or payout_amount > 0 else 'lost'
        settlement_reason = 'CASHBACK_BONUS' if (not verdict and payout_amount > 0) else None
        updated_rows = await db.update_bet_settlement(
            str(bet.get('tx_id') or ''),
            status=status,
            payout_amount=payout_amount,
            reason=settlement_reason,
        )
        updated = updated_rows[0] if updated_rows else {**bet, 'status': status, 'payout_amount': payout_amount}
        await log_operator_event(
            'bet_won' if verdict else 'bet_lost',
            updated,
            intent=dict(intent) if intent else None,
            match=dict(match) if match else None,
            extra={'score': match.get('score'), 'bonus_result': bonus_result},
        )
        await notify_bet_settled(updated, intent=dict(intent) if intent else None, match=dict(match) if match else None)

        # Gamification hook — fire-and-forget, never blocks settlement
        try:
            if sender_wallet:
                asyncio.create_task(_gamification_on_bet_settled(
                    wallet=sender_wallet,
                    bet_tx_id=str(bet.get('tx_id') or ''),
                    amount_prizm=float(bet.get('amount_prizm') or 0),
                    odds=odds_fixed,
                    won=verdict,
                    league=str(match.get('league') or ''),
                    sport=str(match.get('sport') or ''),
                ))
        except Exception as _gex:
            log.warning('[GAMIFICATION] hook error tx=%s: %s', str(bet.get('tx_id') or '')[:18], _gex)

        settled += 1
        log.info('[SETTLED] tx=%s status=%s score=%s', str(bet.get('tx_id') or '')[:18], status, match.get('score'))

    return settled


async def main() -> None:
    log.info('Starting v3 settler loop')
    while True:
        try:
            settled = await run_once()
            if settled:
                log.info('v3 settler updated %s bet(s)', settled)
        except Exception as exc:
            log.error('v3 settler loop error: %s', exc)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == '__main__':
    asyncio.run(main())
