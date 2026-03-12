/**
 * PrizmBet v3 - Wallet Cabinet UI
 */
import { clearIntentRecords, getWalletAddress, saveWalletAddress } from './storage.js';
import { escapeHtml } from './utils.js';
import { getCabinetData, syncWalletInput } from './bet_slip.js';
import { showToast } from './notifications.js';
import { formatNumber, t } from './i18n.js';

let initialized = false;
const dom = {};

const RANK_LABELS = {
    Observer: 'rank.start',
    Runner: 'rank.player',
    Operator: 'rank.tactic',
    Strategist: 'rank.pro',
    Imperator: 'rank.emperor',
    '?????': 'rank.start',
    '?????': 'rank.player',
    '??????': 'rank.tactic',
    '?????': 'rank.pro',
    '?????????': 'rank.emperor',
};

export function initHistoryUI() {
    if (initialized) return;

    Object.assign(dom, {
        modal: document.getElementById('historyModal'),
        walletInput: document.getElementById('cabinetWalletInput'),
        modeBadge: document.getElementById('cabinetModeBadge'),
        rankTitle: document.getElementById('cabinetRankTitle'),
        rankHint: document.getElementById('cabinetRankHint'),
        stats: document.getElementById('cabinetStats'),
        feed: document.getElementById('historyList'),
    });

    dom.walletInput?.addEventListener('input', () => {
        const wallet = normalizeWallet(dom.walletInput.value);
        dom.walletInput.value = wallet;
        saveWalletAddress(wallet);
        syncWalletInput(wallet);
        window.dispatchEvent(new CustomEvent('prizmbet:wallet-changed', {
            detail: { wallet, source: 'cabinet' },
        }));
    });

    dom.walletInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') openHistory();
    });

    window.addEventListener('prizmbet:intent-updated', () => {
        if (dom.modal?.classList.contains('show')) openHistory();
    });

    window.addEventListener('prizmbet:language-changed', () => {
        if (dom.modal?.classList.contains('show')) renderCabinet();
    });

    initialized = true;
}

export async function openHistory() {
    initHistoryUI();
    if (!dom.modal) return;

    if (dom.walletInput && !dom.walletInput.value) {
        dom.walletInput.value = getWalletAddress();
    }

    dom.modal.classList.add('show');
    await renderCabinet();
}

export function closeHistory() {
    dom.modal?.classList.remove('show');
}

export async function clearHistory() {
    if (!confirm(getConfirmText())) return;
    clearIntentRecords();
    showToast(getClearedText());
    await renderCabinet();
}

async function renderCabinet() {
    const wallet = normalizeWallet(dom.walletInput?.value || getWalletAddress());
    if (!wallet) {
        renderEmptyCabinet(getWalletPrompt());
        return;
    }

    saveWalletAddress(wallet);
    syncWalletInput(wallet);
    if (dom.walletInput) dom.walletInput.value = wallet;

    if (dom.feed) {
        dom.feed.innerHTML = `<div class="cabinet-empty">${escapeHtml(t('common.loadingCabinet'))}</div>`;
    }

    try {
        const data = await getCabinetData(wallet);
        renderStats(data);
        renderFeed(data.feed || []);
    } catch (_) {
        renderEmptyCabinet(getCabinetErrorText());
    }
}

function renderStats(data) {
    if (dom.modeBadge) {
        const isLive = data.mode === 'live';
        dom.modeBadge.textContent = isLive ? getLiveModeText() : getLocalModeText();
        dom.modeBadge.className = `coupon-badge ${isLive ? 'coupon-badge--live' : 'coupon-badge--local'}`;
    }

    if (dom.rankTitle) {
        dom.rankTitle.textContent = translateRank(data.rank?.current || 'Observer');
    }

    if (dom.rankHint) {
        dom.rankHint.textContent = data.rank?.next
            ? getNextRankText(data.rank.next.name, data.rank.next.remaining_prizm)
            : getMaxRankText();
    }

    if (dom.stats) {
        dom.stats.innerHTML = `
            ${renderStatCard(getStatCoupons(), data.stats?.total_intents || 0, getStatCouponsHint())}
            ${renderStatCard(getStatWaiting(), data.stats?.waiting_payment || 0, getStatWaitingHint())}
            ${renderStatCard(getStatAccepted(), data.stats?.accepted || 0, getStatAcceptedHint())}
            ${renderStatCard(getStatRejected(), data.stats?.rejected || 0, getStatRejectedHint())}
            ${renderStatCard(getStatWon(), data.stats?.won || 0, getStatWonHint())}
            ${renderStatCard(getStatTurnover(), `${formatNumber(data.stats?.turnover_prizm || 0, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} PZM`, getStatTurnoverHint())}
        `;
    }
}

function renderFeed(items) {
    if (!dom.feed) return;
    if (!items.length) {
        dom.feed.innerHTML = previewMarkup(getPreviewText());
        return;
    }

    dom.feed.innerHTML = items.map((item) => {
        const statusClass = item.status ? `cabinet-record--${escapeHtml(item.status)}` : '';
        return `
            <article class="cabinet-record ${statusClass}">
                <div class="cabinet-record-title">${escapeHtml(item.title)}</div>
                <div class="cabinet-record-subtitle">${escapeHtml(item.subtitle || '')}</div>
                <div class="cabinet-record-meta">${escapeHtml(item.meta || '')}</div>
            </article>
        `;
    }).join('');
}

function renderEmptyCabinet(message) {
    if (dom.modeBadge) {
        dom.modeBadge.textContent = getLocalModeText();
        dom.modeBadge.className = 'coupon-badge coupon-badge--local';
    }
    if (dom.rankTitle) dom.rankTitle.textContent = translateRank('Observer');
    if (dom.rankHint) dom.rankHint.textContent = getFirstCouponHint();
    if (dom.stats) dom.stats.innerHTML = '';
    if (dom.feed) dom.feed.innerHTML = previewMarkup(message);
}

function previewMarkup(message) {
    return `
        <div class="cabinet-empty">
            <strong>${escapeHtml(getPreviewHeadline())}</strong>
            <div class="cabinet-empty-copy">${escapeHtml(message)}</div>
            <div class="cabinet-preview">
                <div class="cabinet-preview-item"><span>${escapeHtml(getPreviewCodeLabel())}</span><span>${escapeHtml(getPreviewCodeValue())}</span></div>
                <div class="cabinet-preview-item"><span>${escapeHtml(getPreviewAcceptanceLabel())}</span><span>${escapeHtml(getPreviewAcceptanceValue())}</span></div>
                <div class="cabinet-preview-item"><span>${escapeHtml(getPreviewSettlementLabel())}</span><span>${escapeHtml(getPreviewSettlementValue())}</span></div>
            </div>
        </div>
    `;
}

function renderStatCard(label, value, hint) {
    return `
        <div class="cabinet-stat-card">
            <div class="cabinet-stat-label">${escapeHtml(label)}</div>
            <div class="cabinet-stat-value">${escapeHtml(value)}</div>
            <div class="cabinet-stat-hint">${escapeHtml(hint)}</div>
        </div>
    `;
}

function translateRank(rank) {
    return t(RANK_LABELS[rank] || 'rank.start');
}

function normalizeWallet(value) {
    return String(value || '').trim().toUpperCase();
}

function getConfirmText() {
    return t('cabinet.clear') + '?';
}
function getClearedText() {
    return t('cabinet.clear') + '.';
}
function getWalletPrompt() {
    return t('cabinet.wallet') + ' PRIZM, ????? ??????? ??????? ? ??????? ??????? ?? ???????.';
}
function getCabinetErrorText() {
    return t('cabinet.title') + ': ?????? ???????? ??????????.';
}
function getLiveModeText() {
    return getIsEn() ? 'Live system statuses' : '??????? ?? ???????';
}
function getLocalModeText() {
    return getIsEn() ? 'History on this device' : '??????? ?? ???? ??????????';
}
function getNextRankText(name, remaining) {
    return getIsEn()
        ? `${formatNumber(remaining, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} PRIZM turnover left to ${translateRank(name)}.`
        : `?? ?????? ${translateRank(name)} ???????? ${formatNumber(remaining, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} PRIZM ???????.`;
}
function getMaxRankText() {
    return getIsEn() ? 'Maximum cabinet level reached.' : '???????????? ??????? ???????? ??? ?????????.';
}
function getFirstCouponHint() {
    return getIsEn() ? 'The cabinet will fill after the first issued bet code.' : '??????? ?????????? ????? ??????? ??????? ???? ??????.';
}
function getPreviewText() {
    return getIsEn() ? 'Issued codes, statuses and settlement will appear here after the first coupon.' : '????? ??????? ?????? ????? ???????? ????, ???????, ?????? ? ??????? ?? ?????? ????????.';
}
function getPreviewHeadline() {
    return getIsEn() ? 'The cabinet appears after the first coupon.' : '??????? ???????? ????? ??????? ??????.';
}
function getPreviewCodeLabel() {
    return getIsEn() ? 'Bet code' : '??? ??????';
}
function getPreviewCodeValue() {
    return getIsEn() ? 'waiting for transfer' : '??????? ???????';
}
function getPreviewAcceptanceLabel() {
    return getIsEn() ? 'Acceptance' : '????????';
}
function getPreviewAcceptanceValue() {
    return getIsEn() ? 'after transfer validation' : '????? ???????? ????????';
}
function getPreviewSettlementLabel() {
    return getIsEn() ? 'Settlement' : '??????';
}
function getPreviewSettlementValue() {
    return getIsEn() ? 'win, loss or rejected' : 'win, loss ??? ??????????';
}
function getStatCoupons() { return getIsEn() ? 'Coupons' : '??????'; }
function getStatCouponsHint() { return getIsEn() ? 'Issued codes' : '???????? ?????'; }
function getStatWaiting() { return getIsEn() ? 'Waiting' : '????'; }
function getStatWaitingHint() { return getIsEn() ? 'Waiting for transfer' : '??????? ???????'; }
function getStatAccepted() { return getIsEn() ? 'Accepted' : '???????'; }
function getStatAcceptedHint() { return getIsEn() ? 'Confirmed by system' : '???????????? ????????'; }
function getStatRejected() { return getIsEn() ? 'Rejected' : '?????????'; }
function getStatRejectedHint() { return getIsEn() ? 'Did not pass validation' : '?? ?????? ????????'; }
function getStatWon() { return getIsEn() ? 'Won' : '????????'; }
function getStatWonHint() { return getIsEn() ? 'Settled as wins' : '?????????? ??? ???????'; }
function getStatTurnover() { return getIsEn() ? 'Turnover' : '??????'; }
function getStatTurnoverHint() { return getIsEn() ? 'Counted betting volume' : '???????? ????? ??????'; }
function getIsEn() { return document.documentElement.lang === 'en'; }
