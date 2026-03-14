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
    Beginner: 'rank.start',
    Player: 'rank.player',
    Regular: 'rank.tactic',
    Pro: 'rank.pro',
    Master: 'rank.emperor',
    'Старт': 'rank.start',
    'Начинающий игрок': 'rank.start',
    'Игрок': 'rank.player',
    'Тактик': 'rank.tactic',
    'Постоянный игрок': 'rank.tactic',
    'Профи': 'rank.pro',
    'Император': 'rank.emperor',
    'Мастер': 'rank.emperor',
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
    if (dom.rankTitle) dom.rankTitle.textContent = translateRank('Beginner');
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
    return getIsEn()
        ? 'Enter a PRIZM wallet to open issued codes and bet statuses.'
        : 'Введите PRIZM-кошелёк, чтобы увидеть выпущенные коды и статусы ставок.';
}
function getCabinetErrorText() {
    return getIsEn()
        ? 'The cabinet data could not be loaded.'
        : 'Не удалось загрузить данные кабинета.';
}
function getLiveModeText() {
    return getIsEn() ? 'System statuses' : 'Статусы из системы';
}
function getLocalModeText() {
    return getIsEn() ? 'History on this device' : 'История на этом устройстве';
}
function getNextRankText(name, remaining) {
    return getIsEn()
        ? `${formatNumber(remaining, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} PRIZM turnover left to ${translateRank(name)}.`
        : `До уровня ${translateRank(name)} осталось ${formatNumber(remaining, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} PRIZM оборота.`;
}
function getMaxRankText() {
    return getIsEn() ? 'Maximum cabinet level reached.' : 'Максимальный уровень кабинета уже достигнут.';
}
function getFirstCouponHint() {
    return getIsEn() ? 'The cabinet will fill after the first issued bet code.' : 'Кабинет заполнится после выпуска первого кода ставки.';
}
function getPreviewText() {
    return getIsEn() ? 'Issued codes, statuses and settlement will appear here after the first coupon.' : 'После первого купона здесь появятся коды, статусы и результаты расчёта.';
}
function getPreviewHeadline() {
    return getIsEn() ? 'The cabinet appears after the first coupon.' : 'Кабинет станет активным после первого купона.';
}
function getPreviewCodeLabel() {
    return getIsEn() ? 'Bet code' : 'Код ставки';
}
function getPreviewCodeValue() {
    return getIsEn() ? 'waiting for transfer' : 'ожидает перевод';
}
function getPreviewAcceptanceLabel() {
    return getIsEn() ? 'Acceptance' : 'Принятие';
}
function getPreviewAcceptanceValue() {
    return getIsEn() ? 'after transfer validation' : 'после проверки перевода';
}
function getPreviewSettlementLabel() {
    return getIsEn() ? 'Settlement' : 'Расчёт';
}
function getPreviewSettlementValue() {
    return getIsEn() ? 'win, loss or rejected' : 'выигрыш, проигрыш или отклонение';
}
function getStatCoupons() { return getIsEn() ? 'Coupons' : 'Купоны'; }
function getStatCouponsHint() { return getIsEn() ? 'Issued codes' : 'Выпущенные коды'; }
function getStatWaiting() { return getIsEn() ? 'Waiting' : 'Ожидание'; }
function getStatWaitingHint() { return getIsEn() ? 'Waiting for transfer' : 'Ожидает перевод'; }
function getStatAccepted() { return getIsEn() ? 'Accepted' : 'Приняты'; }
function getStatAcceptedHint() { return getIsEn() ? 'Confirmed by system' : 'Подтверждены системой'; }
function getStatRejected() { return getIsEn() ? 'Rejected' : 'Отклонены'; }
function getStatRejectedHint() { return getIsEn() ? 'Did not pass validation' : 'Не прошли проверку'; }
function getStatWon() { return getIsEn() ? 'Won' : 'Выиграли'; }
function getStatWonHint() { return getIsEn() ? 'Settled as wins' : 'Рассчитаны как выигрыш'; }
function getStatTurnover() { return getIsEn() ? 'Turnover' : 'Оборот'; }
function getStatTurnoverHint() { return getIsEn() ? 'Counted betting volume' : 'Учтённый объём ставок'; }
function getIsEn() { return document.documentElement.lang === 'en'; }
