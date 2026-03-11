/**
 * PrizmBet v3 - Smart Coupon Module
 */
import { showToast } from './notifications.js';
import { escapeHtml } from './utils.js';
import {
    getWalletAddress,
    saveWalletAddress,
    getIntentRecords,
    upsertIntentRecord,
} from './storage.js';

const MASTER_WALLET = 'PRIZM-4N7T-L2A7-RQZA-5BETW';
const MIN_BET = 1500;
const MAX_BET = 200000;
const INTENT_TTL_MS = 15 * 60 * 1000;
const STATUS_LABELS = {
    draft: 'Черновик',
    awaiting_payment: 'Ожидает перевод',
    accepted: 'Принята',
    rejected: 'Отклонена',
    expired: 'Истёк',
    won: 'Выиграла',
    lost: 'Проиграла',
};
const REJECT_LABELS = {
    LATE_BET: 'Ставка пришла позже безопасного окна',
    SENDER_MISMATCH: 'Перевод пришёл с другого кошелька',
    INVALID_INTENT: 'Код ставки не распознан',
    INTENT_EXPIRED: 'Срок жизни кода истёк',
};

export let currentBet = null;

let activeIntent = null;
let apiBase = '';
let apiLive = false;
let apiCheckPromise = null;
let domBound = false;
let countdownStarted = false;

const dom = {};

export function initSmartBetting() {
    bindDom();
    apiBase = detectApiBase();
    syncWalletInput(getWalletAddress());
    calcPayout();
    ensureApiStatus();

    if (!countdownStarted) {
        countdownStarted = true;
        window.setInterval(() => {
            if (!dom.slip || !dom.slip.classList.contains('show') || !activeIntent) return;
            const normalized = normalizeIntentRecord(activeIntent);
            const changed = normalized.status !== activeIntent.status || normalized.reject_reason !== activeIntent.reject_reason;
            activeIntent = normalized;
            if (changed) {
                upsertIntentRecord(activeIntent);
                dispatchIntentUpdate();
            }
            renderCoupon();
        }, 1000);
    }

    window.removeEventListener('prizmbet:wallet-changed', onExternalWalletChange);
    window.addEventListener('prizmbet:wallet-changed', onExternalWalletChange);
}

function bindDom() {
    if (domBound) return;
    Object.assign(dom, {
        slip: document.getElementById('betSlip'),
        match: document.getElementById('bsMatch'),
        meta: document.getElementById('bsMeta'),
        outcome: document.getElementById('bsOutcome'),
        coef: document.getElementById('bsCoef'),
        amountInput: document.getElementById('bsInput'),
        walletInput: document.getElementById('bsWalletInput'),
        payout: document.getElementById('bsPayout'),
        flowHint: document.getElementById('bsFlowHint'),
        apiBadge: document.getElementById('bsApiBadge'),
        statusPill: document.getElementById('bsStatusPill'),
        issuedBlock: document.getElementById('bsIssuedBlock'),
        intentHash: document.getElementById('bsIntentHash'),
        intentCountdown: document.getElementById('bsIntentCountdown'),
        transferInstructions: document.getElementById('bsTransferInstructions'),
        timeline: document.getElementById('bsTimeline'),
        primaryAction: document.getElementById('bsPrimaryAction'),
    });

    dom.walletInput?.addEventListener('input', () => {
        const wallet = normalizeWallet(dom.walletInput.value);
        dom.walletInput.value = wallet;
        saveWalletAddress(wallet);
        window.dispatchEvent(new CustomEvent('prizmbet:wallet-changed', {
            detail: { wallet, source: 'coupon' },
        }));
        if (currentBet) {
            activeIntent = findRelatedIntent(currentBet, wallet);
            renderCoupon();
        }
    });

    dom.amountInput?.addEventListener('input', () => {
        calcPayout();
        renderCoupon();
    });

    domBound = true;
}

function onExternalWalletChange(event) {
    const nextWallet = normalizeWallet(event?.detail?.wallet || getWalletAddress());
    if (dom.walletInput && document.activeElement !== dom.walletInput) {
        dom.walletInput.value = nextWallet;
    }
    if (currentBet) {
        activeIntent = findRelatedIntent(currentBet, nextWallet);
        renderCoupon();
    }
}

export function closeBetSlip() {
    if (dom.slip) dom.slip.classList.remove('show');
}

export function openBetSlip(betData, betType, coef) {
    initSmartBetting();
    currentBet = {
        ...betData,
        betType,
        coef,
    };
    activeIntent = findRelatedIntent(currentBet, normalizeWallet(dom.walletInput?.value || getWalletAddress()));

    if (dom.match) dom.match.textContent = currentBet.teams;
    if (dom.meta) dom.meta.textContent = `${currentBet.league} • #${currentBet.id}`;
    if (dom.outcome) dom.outcome.textContent = betType;
    if (dom.coef) dom.coef.textContent = coef;
    if (dom.walletInput && !dom.walletInput.value) dom.walletInput.value = getWalletAddress();

    calcPayout();
    renderCoupon();
    ensureApiStatus(true).then(() => renderCoupon());

    if (dom.slip) dom.slip.classList.add('show');
    if (navigator.vibrate) navigator.vibrate(30);
}

export function calcPayout() {
    const amount = Number(dom.amountInput?.value || 0);
    const coef = Number(dom.coef?.textContent || 0);
    if (dom.payout) {
        dom.payout.textContent = formatNumber(amount * coef);
    }
}

export async function copyBetSlipData() {
    initSmartBetting();
    if (!currentBet) return;

    const form = getFormState();
    if (!form.wallet) {
        dom.walletInput?.focus();
        showToast('Введите кошелёк игрока, чтобы выпустить код ставки.');
        return;
    }
    if (form.amount < MIN_BET) {
        dom.amountInput?.focus();
        showToast(`Минимальная ставка — ${formatNumber(MIN_BET)} PRIZM.`);
        return;
    }
    if (form.amount > MAX_BET) {
        dom.amountInput?.focus();
        showToast(`Максимальная ставка — ${formatNumber(MAX_BET)} PRIZM.`);
        return;
    }
    if (!form.coef || form.coef < 1.01) {
        showToast('По этому исходу сейчас нет валидного коэффициента.');
        return;
    }

    const synced = activeIntent && isIntentInSync(activeIntent, form);
    if (synced && activeIntent.status === 'awaiting_payment') {
        await copyIntentCode();
        return;
    }
    if (synced && ['accepted', 'rejected', 'expired', 'won', 'lost'].includes(activeIntent.status)) {
        closeBetSlip();
        if (typeof window.openHistory === 'function') window.openHistory();
        return;
    }

    await issueIntent(form);
}

export async function copyIntentCode() {
    if (!activeIntent?.intent_hash) return;
    await copyText(activeIntent.intent_hash);
    showToast('Intent-код скопирован. Вставьте только его в сообщение перевода.');
}

export async function refreshSlipStatus() {
    if (!activeIntent?.intent_hash) {
        showToast('Сначала выпустите код ставки.');
        return;
    }

    activeIntent = normalizeIntentRecord(activeIntent);
    if (!apiLive || !apiBase) {
        upsertIntentRecord(activeIntent);
        renderCoupon();
        dispatchIntentUpdate();
        showToast('Онлайн API недоступен. Купон работает в локальном режиме.');
        return;
    }

    try {
        const response = await fetch(`${apiBase}/api/intents/${encodeURIComponent(activeIntent.intent_hash)}`, { mode: 'cors' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        syncIntentFromApi(payload);
        showToast('Статус купона обновлён.');
    } catch (error) {
        showToast('Не удалось обновить статус из API.');
    }
}

export async function getCabinetData(wallet) {
    const normalizedWallet = normalizeWallet(wallet);
    if (!normalizedWallet) {
        return {
            wallet: '',
            mode: apiLive ? 'live' : 'local',
            rank: deriveRank(0, 0),
            stats: {
                waiting_payment: 0,
                accepted: 0,
                rejected: 0,
                won: 0,
                lost: 0,
                turnover_prizm: 0,
                total_intents: 0,
            },
            feed: [],
        };
    }

    await ensureApiStatus();
    if (apiLive && apiBase) {
        try {
            const response = await fetch(`${apiBase}/api/wallets/${encodeURIComponent(normalizedWallet)}/dashboard`, { mode: 'cors' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const payload = await response.json();
            return mapDashboardToCabinet(normalizedWallet, payload);
        } catch (_) {
            // Fallback below.
        }
    }

    return buildLocalCabinet(normalizedWallet);
}

export function syncWalletInput(wallet) {
    const normalized = normalizeWallet(wallet);
    saveWalletAddress(normalized);
    if (dom.walletInput && document.activeElement !== dom.walletInput) {
        dom.walletInput.value = normalized;
    }
}

export function copyWallet(btn) {
    copyText(MASTER_WALLET).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '✅ Скопировано!';
        setTimeout(() => { btn.innerHTML = originalText; }, 1800);
    });
}

export function toggleMyBets() {
    if (typeof window.openHistory === 'function') window.openHistory();
}

export function checkMyBets() {
    if (typeof window.openHistory === 'function') window.openHistory();
}

async function issueIntent(form) {
    await ensureApiStatus();

    const intent = buildLocalIntent(form);
    if (apiLive && apiBase) {
        try {
            const response = await fetch(`${apiBase}/api/intents`, {
                method: 'POST',
                mode: 'cors',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    match_id: String(currentBet.id || ''),
                    outcome: form.apiOutcome,
                    sender_wallet: form.wallet,
                }),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const payload = await response.json();
            intent.intent_hash = payload.intent_hash || intent.intent_hash;
            intent.odds_fixed = Number(payload.odds_fixed || intent.odds_fixed);
            intent.expires_at = payload.expires_at || intent.expires_at;
            intent.mode = 'live';
            pushTimeline(intent, 'Код сохранён в системе', 'Код сохранён в системе и будет проверен при поступлении перевода.');
        } catch (_) {
            intent.mode = 'local';
            pushTimeline(intent, 'Переход в локальный режим', 'Intent API недоступен, поэтому купон временно работает локально.');
        }
    }

    activeIntent = normalizeIntentRecord(intent);
    upsertIntentRecord(activeIntent);
    renderCoupon();
    dispatchIntentUpdate();
    showToast(activeIntent.mode === 'live' ? 'Код ставки выпущен через API.' : 'Код ставки выпущен в локальном режиме.');
}

function buildLocalIntent(form) {
    return {
        intent_hash: randomHash(),
        sender_wallet: form.wallet,
        amount_prizm: form.amount,
        odds_fixed: form.coef,
        outcome: currentBet.betType,
        api_outcome: form.apiOutcome,
        match_id: String(currentBet.id || ''),
        match_label: currentBet.teams || form.matchLabel,
        league: currentBet.league || '',
        match_time: currentBet.datetime || '',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + INTENT_TTL_MS).toISOString(),
        status: 'awaiting_payment',
        mode: apiLive ? 'live' : 'local',
        reject_reason: '',
        timeline: [
            {
                title: 'Купон выпущен',
                description: 'Сайт зафиксировал исход и подготовил короткий intent-код для перевода.',
                at: new Date().toISOString(),
            },
        ],
    };
}

function renderCoupon() {
    if (!domBound || !currentBet) return;

    activeIntent = normalizeIntentRecord(activeIntent);
    const form = getFormState();
    const statusMeta = getStatusMeta(activeIntent?.status || 'draft');

    if (dom.match) dom.match.textContent = currentBet.teams || form.matchLabel;
    if (dom.meta) dom.meta.textContent = `${currentBet.league || 'Без лиги'} • #${currentBet.id || '—'}`;
    if (dom.outcome) dom.outcome.textContent = currentBet.betType || '—';
    if (dom.coef) dom.coef.textContent = formatOdd(currentBet.coef);
    if (dom.walletInput && document.activeElement !== dom.walletInput && !dom.walletInput.value) {
        dom.walletInput.value = getWalletAddress();
    }

    if (dom.apiBadge) {
        dom.apiBadge.textContent = apiLive ? 'Онлайн API' : 'Локальный режим';
        dom.apiBadge.className = `coupon-badge ${apiLive ? 'coupon-badge--live' : 'coupon-badge--local'}`;
    }
    if (dom.statusPill) {
        dom.statusPill.textContent = statusMeta.label;
        dom.statusPill.className = `coupon-status ${statusMeta.className}`;
    }
    if (dom.primaryAction) {
        dom.primaryAction.textContent = getPrimaryActionLabel(form);
    }
    if (dom.flowHint) {
        dom.flowHint.textContent = getFlowHint(form, statusMeta);
    }

    if (!activeIntent?.intent_hash) {
        dom.issuedBlock?.classList.add('hidden');
        if (dom.timeline) {
            dom.timeline.innerHTML = `
                <div class="coupon-timeline-item">
                    <strong>Следующий шаг</strong>
                    <div>Введите кошелёк и сумму, затем выпустите короткий intent-код. Старый длинный комментарий больше не нужен.</div>
                </div>
            `;
        }
        return;
    }

    if (dom.intentHash) dom.intentHash.textContent = activeIntent.intent_hash;
    if (dom.intentCountdown) dom.intentCountdown.textContent = formatCountdown(activeIntent.expires_at);
    if (dom.transferInstructions) dom.transferInstructions.textContent = buildTransferInstructions(activeIntent);
    dom.issuedBlock?.classList.remove('hidden');
    renderTimeline(activeIntent);
}

function renderTimeline(intent) {
    if (!dom.timeline) return;
    const items = (intent.timeline || []).slice().reverse();
    dom.timeline.innerHTML = items.map((item) => `
        <div class="coupon-timeline-item">
            <strong>${escapeHtml(item.title)}</strong>
            <div>${escapeHtml(item.description)}</div>
            <small>${escapeHtml(formatDateTime(item.at))}</small>
        </div>
    `).join('');
}

function syncIntentFromApi(payload) {
    activeIntent = normalizeIntentRecord({
        ...activeIntent,
        status: payload.status || activeIntent.status,
        expires_at: payload.intent?.expires_at || activeIntent.expires_at,
        reject_reason: payload.bet?.reject_reason || activeIntent.reject_reason,
        mode: 'live',
    });
    pushTimeline(
        activeIntent,
        'Статус синхронизирован',
        payload.bet
            ? `Система вернула ${STATUS_LABELS[activeIntent.status] || activeIntent.status}.`
            : `Intent пока без связанной транзакции, текущее состояние: ${STATUS_LABELS[activeIntent.status] || activeIntent.status}.`
    );
    upsertIntentRecord(activeIntent);
    renderCoupon();
    dispatchIntentUpdate();
}

function dispatchIntentUpdate() {
    window.dispatchEvent(new CustomEvent('prizmbet:intent-updated', {
        detail: { intent: activeIntent },
    }));
}

function getFormState() {
    const amount = Number(dom.amountInput?.value || 0);
    return {
        wallet: normalizeWallet(dom.walletInput?.value || getWalletAddress()),
        amount,
        coef: toNumber(currentBet?.coef || 0),
        apiOutcome: mapOutcomeToApiOutcome(currentBet?.betType),
        matchLabel: currentBet?.teams || '',
    };
}

function findRelatedIntent(bet, wallet) {
    if (!bet) return null;
    const targetWallet = normalizeWallet(wallet);
    const targetOutcome = mapOutcomeToApiOutcome(bet.betType);
    const records = getIntentRecords()
        .map((item) => normalizeIntentRecord(item))
        .filter((item) => {
            if (String(item.match_id) !== String(bet.id || '')) return false;
            if (String(item.api_outcome || '') !== String(targetOutcome)) return false;
            if (targetWallet && normalizeWallet(item.sender_wallet) !== targetWallet) return false;
            return true;
        })
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    return records[0] || null;
}

function isIntentInSync(intent, form) {
    if (!intent) return false;
    return normalizeWallet(intent.sender_wallet) === form.wallet
        && Number(intent.amount_prizm || 0) === Number(form.amount || 0)
        && String(intent.match_id || '') === String(currentBet?.id || '')
        && String(intent.api_outcome || '') === String(form.apiOutcome || '');
}

function normalizeIntentRecord(record) {
    if (!record) return null;
    const normalized = { ...record };
    if (normalized.status === 'awaiting_payment' && isExpired(normalized)) {
        normalized.status = 'expired';
        normalized.reject_reason = normalized.reject_reason || 'INTENT_EXPIRED';
        const hasExpiryEvent = (normalized.timeline || []).some((item) => item.title === 'Срок кода истёк');
        if (!hasExpiryEvent) {
            pushTimeline(normalized, 'Срок кода истёк', 'Код не был подтверждён переводом до завершения окна intent.');
        }
    }
    return normalized;
}

function isExpired(record) {
    const expiresAt = new Date(record?.expires_at || 0).getTime();
    return Boolean(expiresAt) && expiresAt <= Date.now();
}

async function ensureApiStatus(force = false) {
    if (!apiBase) {
        apiLive = false;
        return false;
    }
    if (apiCheckPromise && !force) return apiCheckPromise;

    apiCheckPromise = (async () => {
        try {
            const response = await fetch(`${apiBase}/health`, { mode: 'cors' });
            apiLive = response.ok;
        } catch (_) {
            apiLive = false;
        }
        return apiLive;
    })();

    return apiCheckPromise;
}

function detectApiBase() {
    const explicit = String(window.PRIZMBET_INTENT_API_BASE || '').trim();
    if (explicit) return explicit.replace(/\/$/, '');
    if (['localhost', '127.0.0.1'].includes(window.location.hostname)) {
        return 'http://127.0.0.1:8081';
    }
    return '';
}

function mapOutcomeToApiOutcome(outcome) {
    const normalized = String(outcome || '').trim().toUpperCase();
    if (normalized === 'П1') return 'P1';
    if (normalized === 'П2') return 'P2';
    if (normalized === 'X') return 'X';
    return normalized;
}

function getPrimaryActionLabel(form) {
    if (!activeIntent?.intent_hash) return 'Выпустить код ставки';
    if (isIntentInSync(activeIntent, form)) {
        if (activeIntent.status === 'awaiting_payment') return 'Скопировать intent-код';
        if (['accepted', 'rejected', 'expired', 'won', 'lost'].includes(activeIntent.status)) return 'Открыть кабинет';
    }
    return 'Выпустить новый код';
}

function getFlowHint(form, statusMeta) {
    if (!activeIntent?.intent_hash) {
        return 'Введите кошелёк и сумму. Сайт выпустит короткий код ставки и зафиксирует коэффициент.';
    }
    if (activeIntent.status === 'awaiting_payment') {
        if (isIntentInSync(activeIntent, form)) {
            return 'Код уже выпущен. Отправьте перевод и вставьте в сообщение только этот intent-код.';
        }
        return 'Параметры купона изменились. Выпустите новый код, чтобы зафиксировать обновлённую ставку.';
    }
    return statusMeta.hint;
}

function getStatusMeta(status) {
    if (status === 'awaiting_payment') {
        return {
            label: STATUS_LABELS.awaiting_payment,
            className: 'coupon-status--waiting',
            hint: 'Купон ожидает перевод с указанным кодом и кошельком.',
        };
    }
    if (status === 'accepted') {
        return {
            label: STATUS_LABELS.accepted,
            className: 'coupon-status--accepted',
            hint: 'Listener увидел перевод и принял ставку. Дальше следите за расчётом в кабинете.',
        };
    }
    if (status === 'rejected') {
        return {
            label: STATUS_LABELS.rejected,
            className: 'coupon-status--rejected',
            hint: REJECT_LABELS[activeIntent?.reject_reason] || 'Ставка была отклонена правилами системы.',
        };
    }
    if (status === 'expired') {
        return {
            label: STATUS_LABELS.expired,
            className: 'coupon-status--expired',
            hint: 'Окно intent завершилось. Для новой попытки выпустите новый код.',
        };
    }
    if (status === 'won' || status === 'lost') {
        return {
            label: STATUS_LABELS[status],
            className: 'coupon-status--settled',
            hint: status === 'won' ? 'Ставка рассчитана как выигрышная.' : 'Ставка рассчитана как проигрышная.',
        };
    }
    return {
        label: STATUS_LABELS.draft,
        className: 'coupon-status--draft',
        hint: 'Купон ещё не выпущен.',
    };
}

function buildTransferInstructions(intent) {
    return `Отправьте ${formatNumber(intent.amount_prizm)} PRIZM на ${MASTER_WALLET}. В сообщение перевода вставьте только код ${intent.intent_hash}. ${apiLive ? 'Статус подтянется автоматически.' : 'Пока API недоступен, купон сохранится локально и поможет пройти весь сценарий.'}`;
}

function buildLocalCabinet(wallet) {
    const records = getIntentRecords()
        .map((item) => normalizeIntentRecord(item))
        .filter((item) => normalizeWallet(item.sender_wallet) === wallet)
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

    let waiting_payment = 0;
    let accepted = 0;
    let rejected = 0;
    let won = 0;
    let lost = 0;
    let turnover_prizm = 0;

    records.forEach((record) => {
        if (record.status === 'awaiting_payment') waiting_payment += 1;
        if (record.status === 'accepted') accepted += 1;
        if (record.status === 'rejected' || record.status === 'expired') rejected += 1;
        if (record.status === 'won') won += 1;
        if (record.status === 'lost') lost += 1;
        if (['accepted', 'won', 'lost'].includes(record.status)) {
            turnover_prizm += Number(record.amount_prizm || 0);
        }
    });

    return {
        wallet,
        mode: 'local',
        rank: deriveRank(turnover_prizm, accepted + won + lost),
        stats: {
            waiting_payment,
            accepted,
            rejected,
            won,
            lost,
            turnover_prizm,
            total_intents: records.length,
        },
        feed: records.slice(0, 12).map((record) => ({
            title: record.match_label || `Матч #${record.match_id}`,
            subtitle: `${record.outcome} @ ${formatNumber(record.odds_fixed)} • ${formatNumber(record.amount_prizm)} PRIZM`,
            meta: `${STATUS_LABELS[record.status] || record.status}${record.reject_reason ? ` • ${REJECT_LABELS[record.reject_reason] || record.reject_reason}` : ''} • ${formatDateTime(record.created_at)}`,
            status: record.status,
        })),
    };
}

function mapDashboardToCabinet(wallet, payload) {
    const rank = payload.rank || deriveRank(Number(payload.stats?.turnover_prizm || 0), Number(payload.rank?.accepted_count || 0));
    const recentBets = Array.isArray(payload.recent_bets) ? payload.recent_bets : [];
    const recentIntents = Array.isArray(payload.recent_intents) ? payload.recent_intents : [];

    const feedFromBets = recentBets.map((bet) => ({
        title: bet.match_label || [bet.team1, bet.team2].filter(Boolean).join(' vs ') || `Матч #${bet.match_id || '—'}`,
        subtitle: `${bet.outcome || bet.bet_type || 'Исход'} @ ${formatNumber(bet.odds_fixed || bet.coef)} • ${formatNumber(bet.amount_prizm || bet.amount || 0)} PRIZM`,
        meta: `${STATUS_LABELS[bet.status] || bet.status || 'accepted'} • ${formatDateTime(bet.created_at)}`,
        status: bet.status || 'accepted',
    }));

    const feed = feedFromBets.length ? feedFromBets : recentIntents.map((intent) => ({
        title: `${intent.intent_hash} • матч #${intent.match_id}`,
        subtitle: `${intent.outcome} @ ${formatNumber(intent.odds_fixed)}`,
        meta: `${STATUS_LABELS[intent.status] || intent.status} • ${formatDateTime(intent.created_at || intent.expires_at)}`,
        status: intent.status,
    }));

    return {
        wallet,
        mode: 'live',
        rank,
        stats: {
            waiting_payment: Number(payload.stats?.waiting_payment || 0),
            accepted: Number(payload.stats?.accepted || 0),
            rejected: Number(payload.stats?.rejected || 0),
            won: Number(payload.stats?.won || 0),
            lost: Number(payload.stats?.lost || 0),
            turnover_prizm: Number(payload.stats?.turnover_prizm || 0),
            total_intents: Number(payload.stats?.total_intents || recentIntents.length),
        },
        feed: feed.slice(0, 12),
    };
}

function deriveRank(turnover, acceptedCount) {
    const tiers = [
        { name: 'Observer', threshold: 0 },
        { name: 'Runner', threshold: 1500 },
        { name: 'Operator', threshold: 5000 },
        { name: 'Strategist', threshold: 15000 },
        { name: 'Imperator', threshold: 50000 },
    ];

    let current = tiers[0];
    let next = null;
    for (const tier of tiers) {
        if (turnover >= tier.threshold) current = tier;
        else {
            next = tier;
            break;
        }
    }

    const span = next ? Math.max(next.threshold - current.threshold, 1) : 1;
    const progress = next ? Math.min(100, Math.round(((turnover - current.threshold) / span) * 100)) : 100;

    return {
        current: current.name,
        accepted_count: acceptedCount,
        progress_percent: progress,
        next: next ? {
            name: next.name,
            remaining_prizm: Math.max(next.threshold - turnover, 0),
        } : null,
    };
}

function pushTimeline(record, title, description) {
    const timeline = Array.isArray(record.timeline) ? record.timeline.slice(-7) : [];
    timeline.push({ title, description, at: new Date().toISOString() });
    record.timeline = timeline;
}

function randomHash(length = 6) {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    return Array.from({ length }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
}

function normalizeWallet(value) {
    return String(value || '').trim().toUpperCase();
}

function formatOdd(value) {
    const number = toNumber(value);
    return Number.isFinite(number) ? number.toFixed(2) : '0.00';
}

function toNumber(value) {
    const normalized = String(value ?? '').replace(',', '.').trim();
    const number = Number(normalized);
    return Number.isFinite(number) ? number : 0;
}

function formatNumber(value) {
    const number = Number(value || 0);
    return Number.isFinite(number)
        ? number.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
        : '0';
}

function formatDateTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value || '');
    return date.toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function formatCountdown(expiresAt) {
    const diff = new Date(expiresAt || 0).getTime() - Date.now();
    if (diff <= 0) return '00:00';
    const totalSeconds = Math.floor(diff / 1000);
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    return `${minutes}:${seconds}`;
}

function copyText(text) {
    if (navigator.clipboard?.writeText) {
        return navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
    }
    fallbackCopy(text);
    return Promise.resolve();
}

function fallbackCopy(text) {
    const area = document.createElement('textarea');
    area.value = text;
    area.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
    document.body.appendChild(area);
    area.focus();
    area.select();
    try { document.execCommand('copy'); } catch (_) {}
    document.body.removeChild(area);
}