/**
 * PrizmBet v3 - Smart Coupon Module
 */
import { showToast } from './notifications.js';
import { escapeHtml } from './utils.js';
import { formatDateTime as formatDateTimeI18n, formatNumber as formatNumberI18n, formatOutcomeLabel, t } from './i18n.js';
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
const REJECT_LABELS = {
    LATE_BET: { ru: '?????? ?????? ????? ??????????? ????', en: 'The transfer arrived too late' },
    SENDER_MISMATCH: { ru: '??????? ?????? ? ??????? ????????', en: 'The transfer came from another wallet' },
    INVALID_INTENT: { ru: '??? ?????? ?? ?????????', en: 'The bet code was not recognized' },
    INTENT_EXPIRED: { ru: '???? ????? ???? ?????', en: 'The code expired' },
};

function isEnglish() {
    return document.documentElement.lang === 'en';
}

function getStatusLabel(status) {
    return t(`status.${status}`);
}

function getRejectLabel(code) {
    const item = REJECT_LABELS[code];
    if (!item) return code || '';
    return isEnglish() ? item.en : item.ru;
}

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
        lockedMatch: document.getElementById('bsLockedMatch'),
        lockedOutcome: document.getElementById('bsLockedOutcome'),
        lockedOdds: document.getElementById('bsLockedOdds'),
        lockedAmount: document.getElementById('bsLockedAmount'),
        lockedPayout: document.getElementById('bsLockedPayout'),
        lockedExpiry: document.getElementById('bsLockedExpiry'),
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
        dom.issuedBlock?.classList.add('hidden');
        if (dom.timeline) {
            dom.timeline.innerHTML = `
                <div class="coupon-timeline-item">
                    <strong>Следующий шаг</strong>
                    <div>Укажите кошелёк и сумму, затем выпустите короткий код. После этого в переводе нужен только этот код, без длинного комментария.</div>
                </div>
            `;
        }
        return;
    }

    activeIntent = normalizeIntentRecord(activeIntent);
    if (!apiLive || !apiBase) {
        upsertIntentRecord(activeIntent);
        renderCoupon();
        dispatchIntentUpdate();
        showToast('Онлайн-проверка временно недоступна. Код и история остаются на этом устройстве.');
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
    showToast(activeIntent.mode === 'live' ? 'Код ставки выпущен.' : 'Код ставки сохранён на этом устройстве.');
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
        if (activeIntent?.intent_hash) {
            dom.apiBadge.textContent = apiLive ? 'Статус обновляется онлайн' : 'Код сохранён на этом устройстве';
            dom.apiBadge.className = `coupon-badge ${apiLive ? 'coupon-badge--live' : 'coupon-badge--local'}`;
        } else {
            dom.apiBadge.textContent = 'Купон готов к выпуску';
            dom.apiBadge.className = 'coupon-badge coupon-badge--info';
        }
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

    renderLockedSummary(form);
    if (dom.intentHash) dom.intentHash.textContent = activeIntent.intent_hash;
    if (dom.intentCountdown) dom.intentCountdown.textContent = formatCountdown(activeIntent.expires_at);
    if (dom.transferInstructions) dom.transferInstructions.textContent = buildTransferInstructions(activeIntent);
    dom.issuedBlock?.classList.remove('hidden');
    renderTimeline(activeIntent);
}

function renderLockedSummary(form) {
    if (!activeIntent) return;
    if (dom.lockedMatch) dom.lockedMatch.textContent = activeIntent.match_label || currentBet?.teams || form.matchLabel || '—';
    if (dom.lockedOutcome) dom.lockedOutcome.textContent = activeIntent.outcome || currentBet?.betType || '—';
    if (dom.lockedOdds) dom.lockedOdds.textContent = formatOdd(activeIntent.odds_fixed || form.coef);
    if (dom.lockedAmount) dom.lockedAmount.textContent = `${formatNumber(activeIntent.amount_prizm || form.amount)} PRIZM`;
    if (dom.lockedPayout) dom.lockedPayout.textContent = `${formatNumber((Number(activeIntent.amount_prizm || form.amount) || 0) * (Number(activeIntent.odds_fixed || form.coef) || 0))} PRIZM`;
    if (dom.lockedExpiry) dom.lockedExpiry.textContent = formatDateTime(activeIntent.expires_at);
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
        isEnglish() ? 'Status synchronized' : '?????? ???????????????',
        payload.bet
            ? `${isEnglish() ? 'System returned' : '??????? ???????'} ${getStatusLabel(activeIntent.status) || activeIntent.status}.`
            : `${isEnglish() ? 'No transfer is linked yet, current state:' : 'Intent ???? ??? ????????? ??????????, ??????? ?????????:'} ${getStatusLabel(activeIntent.status) || activeIntent.status}.`
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
    if (!activeIntent?.intent_hash) return t('coupon.issue');
    if (isIntentInSync(activeIntent, form)) {
        if (activeIntent.status === 'awaiting_payment') return t('coupon.copyCode');
        if (['accepted', 'rejected', 'expired', 'won', 'lost'].includes(activeIntent.status)) return t('coupon.openCabinet');
    }
    return isEnglish() ? 'Issue new code' : '????????? ????? ???';
}


function getFlowHint(form, statusMeta) {
    if (!activeIntent?.intent_hash) {
        return isEnglish() ? 'Enter the wallet and amount. The coupon will lock the odds and issue the transfer code.' : '??????? ??????? ? ?????. ????? ??????????? ??????????? ? ???????? ???????? ??? ??? ????????.';
    }
    if (activeIntent.status === 'awaiting_payment') {
        if (isIntentInSync(activeIntent, form)) {
            return isEnglish() ? 'The code is already issued. Send the transfer from the same wallet and use this code.' : '??? ??? ???????. ????????? ??????? ? ????? ?? ???????? ? ???????? ? ????????? ?????? ???? ???.';
        }
        return isEnglish() ? 'The bet parameters changed. Issue a new code to lock the updated coupon.' : '????????? ?????? ??????????. ????????? ????? ???, ????? ?????? ????????????? ?????.';
    }
    return statusMeta.hint;
}


function getStatusMeta(status) {
    if (status === 'awaiting_payment') {
        return {
            label: getStatusLabel('awaiting_payment'),
            className: 'coupon-status--waiting',
            hint: isEnglish() ? 'The code is issued. The system is waiting for a transfer from the same wallet.' : '??? ???????. ??????? ???? ??????? ? ????????? ????? ? ??? ?? ?????????.',
        };
    }
    if (status === 'accepted') {
        return {
            label: getStatusLabel('accepted'),
            className: 'coupon-status--accepted',
            hint: isEnglish() ? 'The transfer was found and the bet is accepted. Follow settlement in the cabinet.' : '??????? ?????? ? ?????? ???????. ?????? ??????? ?? ???????? ? ????????.',
        };
    }
    if (status === 'rejected') {
        return {
            label: getStatusLabel('rejected'),
            className: 'coupon-status--rejected',
            hint: getRejectLabel(activeIntent?.reject_reason) || (isEnglish() ? 'The bet was rejected by system rules.' : '?????? ???? ????????? ????????? ???????.'),
        };
    }
    if (status === 'expired') {
        return {
            label: getStatusLabel('expired'),
            className: 'coupon-status--expired',
            hint: isEnglish() ? 'The coupon window is over. Issue a new code for a new attempt.' : '???? ?????? ???????????. ??? ????? ??????? ????????? ????? ???.',
        };
    }
    if (status === 'won' || status === 'lost') {
        return {
            label: getStatusLabel(status),
            className: 'coupon-status--settled',
            hint: status === 'won'
                ? (isEnglish() ? 'The bet is settled as a win.' : '?????? ?????????? ??? ??????????.')
                : (isEnglish() ? 'The bet is settled as a loss.' : '?????? ?????????? ??? ???????????.'),
        };
    }
    return {
        label: getStatusLabel('draft'),
        className: 'coupon-status--draft',
        hint: isEnglish() ? 'The coupon is not issued yet.' : '????? ??? ?? ???????.',
    };
}


function buildTransferInstructions(intent) {
    const base = isEnglish()
        ? `Send ${formatNumber(intent.amount_prizm)} PRIZM to ${MASTER_WALLET}. Put code ${intent.intent_hash} into the transfer message.`
        : `????????? ${formatNumber(intent.amount_prizm)} PRIZM ?? ${MASTER_WALLET}. ? ????????? ???????? ???????? ?????? ??? ${intent.intent_hash}.`;
    return apiLive
        ? `${base} ${isEnglish() ? 'After the transfer open the cabinet to see the status.' : '????? ???????? ???????? ???????, ????? ??????? ??????.'}`
        : `${base} ${isEnglish() ? 'The code and history are already saved on this device.' : '??? ? ??????? ??? ????????? ?? ???? ??????????.'}`;
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
        if (['accepted', 'won', 'lost'].includes(record.status)) turnover_prizm += Number(record.amount_prizm || 0);
    });

    return {
        wallet,
        mode: 'local',
        rank: deriveRank(turnover_prizm, accepted + won + lost),
        stats: { waiting_payment, accepted, rejected, won, lost, turnover_prizm, total_intents: records.length },
        feed: records.slice(0, 12).map((record) => ({
            title: record.match_label || `${isEnglish() ? 'Match' : '????'} #${record.match_id}`,
            subtitle: `${formatOutcomeLabel(record.outcome)} @ ${formatNumber(record.odds_fixed)} ? ${formatNumber(record.amount_prizm)} PRIZM`,
            meta: `${getStatusLabel(record.status) || record.status}${record.reject_reason ? ` ? ${getRejectLabel(record.reject_reason) || record.reject_reason}` : ''} ? ${formatDateTime(record.created_at)}`,
            status: record.status,
        })),
    };
}


function mapDashboardToCabinet(wallet, payload) {
    const rank = payload.rank || deriveRank(Number(payload.stats?.turnover_prizm || 0), Number(payload.rank?.accepted_count || 0));
    const recentBets = Array.isArray(payload.recent_bets) ? payload.recent_bets : [];
    const recentIntents = Array.isArray(payload.recent_intents) ? payload.recent_intents : [];

    const feedFromBets = recentBets.map((bet) => ({
        title: bet.match_label || [bet.team1, bet.team2].filter(Boolean).join(' vs ') || `${isEnglish() ? 'Match' : '????'} #${bet.match_id || '?'}`,
        subtitle: `${formatOutcomeLabel(bet.outcome || bet.bet_type || (isEnglish() ? 'Outcome' : '?????'))} @ ${formatNumber(bet.odds_fixed || bet.coef)} ? ${formatNumber(bet.amount_prizm || bet.amount || 0)} PRIZM`,
        meta: `${getStatusLabel(bet.status || 'accepted')} ? ${formatDateTime(bet.created_at)}`,
        status: bet.status || 'accepted',
    }));

    const feed = feedFromBets.length ? feedFromBets : recentIntents.map((intent) => ({
        title: `${intent.intent_hash} ? ${isEnglish() ? 'match' : '????'} #${intent.match_id}`,
        subtitle: `${formatOutcomeLabel(intent.outcome)} @ ${formatNumber(intent.odds_fixed)}`,
        meta: `${getStatusLabel(intent.status) || intent.status} ? ${formatDateTime(intent.created_at || intent.expires_at)}`,
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
        { name: 'Старт', threshold: 0 },
        { name: 'Игрок', threshold: 1500 },
        { name: 'Тактик', threshold: 5000 },
        { name: 'Профи', threshold: 15000 },
        { name: 'Император', threshold: 50000 },
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
    return formatNumberI18n(value, { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function formatDateTime(value) {
    return formatDateTimeI18n(value);
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
