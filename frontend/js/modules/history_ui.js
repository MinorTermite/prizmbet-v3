/**
 * PrizmBet v3 - Wallet Cabinet UI
 */
import { clearIntentRecords, getWalletAddress, saveWalletAddress } from './storage.js';
import { escapeHtml } from './utils.js';
import { getCabinetData, syncWalletInput } from './bet_slip.js';
import { showToast } from './notifications.js';

let initialized = false;
const dom = {};

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
    if (dom.modal) dom.modal.classList.remove('show');
}

export async function clearHistory() {
    if (!confirm('Очистить локальную историю intent-купонов на этом устройстве?')) return;
    clearIntentRecords();
    showToast('Локальная история intent-ов очищена.');
    await renderCabinet();
}

async function renderCabinet() {
    const wallet = normalizeWallet(dom.walletInput?.value || getWalletAddress());
    if (!wallet) {
        renderEmptyCabinet('Введите кошелёк PRIZM, чтобы открыть кабинет ставок.');
        return;
    }

    saveWalletAddress(wallet);
    syncWalletInput(wallet);
    if (dom.walletInput) dom.walletInput.value = wallet;

    if (dom.feed) {
        dom.feed.innerHTML = '<div class="cabinet-empty">Загружаем кабинет кошелька…</div>';
    }

    try {
        const data = await getCabinetData(wallet);
        renderStats(data);
        renderFeed(data.feed || []);
    } catch (_) {
        renderEmptyCabinet('Не удалось получить данные кабинета.');
    }
}

function renderStats(data) {
    if (dom.modeBadge) {
        dom.modeBadge.textContent = data.mode === 'live' ? 'LIVE API' : 'LOCAL CACHE';
        dom.modeBadge.className = `coupon-badge ${data.mode === 'live' ? 'coupon-badge--live' : 'coupon-badge--local'}`;
    }
    if (dom.rankTitle) {
        dom.rankTitle.textContent = data.rank?.current || 'Observer';
    }
    if (dom.rankHint) {
        dom.rankHint.textContent = data.rank?.next
            ? `До ${data.rank.next.name} осталось ${formatNumber(data.rank.next.remaining_prizm)} PRIZM turnover.`
            : 'Максимальный preview rank уже достигнут.';
    }
    if (dom.stats) {
        dom.stats.innerHTML = `
            ${renderStatCard('Intent', data.stats?.total_intents || 0, 'Выпущено кодов')}
            ${renderStatCard('Waiting', data.stats?.waiting_payment || 0, 'Ждут перевод')}
            ${renderStatCard('Accepted', data.stats?.accepted || 0, 'Приняты listener-ом')}
            ${renderStatCard('Rejected', data.stats?.rejected || 0, 'Отклонены или истекли')}
            ${renderStatCard('Won', data.stats?.won || 0, 'Выигранные ставки')}
            ${renderStatCard('Turnover', `${formatNumber(data.stats?.turnover_prizm || 0)} PZM`, 'Учтённый объём')}
        `;
    }
}

function renderFeed(items) {
    if (!dom.feed) return;
    if (!items.length) {
        dom.feed.innerHTML = '<div class="cabinet-empty">По этому кошельку ещё нет выпущенных купонов или backend-активности.</div>';
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
        dom.modeBadge.textContent = 'LOCAL CACHE';
        dom.modeBadge.className = 'coupon-badge coupon-badge--local';
    }
    if (dom.rankTitle) dom.rankTitle.textContent = 'Observer';
    if (dom.rankHint) dom.rankHint.textContent = 'Кабинет появится после выпуска первого купона.';
    if (dom.stats) dom.stats.innerHTML = '';
    if (dom.feed) dom.feed.innerHTML = `<div class="cabinet-empty">${escapeHtml(message)}</div>`;
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

function formatNumber(value) {
    const number = Number(value || 0);
    return Number.isFinite(number)
        ? number.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
        : '0';
}

function normalizeWallet(value) {
    return String(value || '').trim().toUpperCase();
}