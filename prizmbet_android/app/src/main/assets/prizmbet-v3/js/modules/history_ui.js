/**
 * PrizmBet v3 - Wallet Cabinet UI
 */
import { clearIntentRecords, getWalletAddress, saveWalletAddress } from './storage.js';
import { escapeHtml } from './utils.js';
import { getCabinetData, syncWalletInput } from './bet_slip.js';
import { showToast } from './notifications.js';

let initialized = false;
const dom = {};

const RANK_LABELS = {
    Observer: 'Старт',
    Runner: 'Игрок',
    Operator: 'Тактик',
    Strategist: 'Профи',
    Imperator: 'Император',
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
    if (!confirm('Очистить сохранённую историю купонов на этом устройстве?')) return;
    clearIntentRecords();
    showToast('История на этом устройстве очищена.');
    await renderCabinet();
}

async function renderCabinet() {
    const wallet = normalizeWallet(dom.walletInput?.value || getWalletAddress());
    if (!wallet) {
        renderEmptyCabinet('Введите кошелёк PRIZM, чтобы открыть кабинет и увидеть статусы по ставкам.');
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
        renderEmptyCabinet('Не удалось получить данные кабинета. Повторите обновление позже.');
    }
}

function renderStats(data) {
    if (dom.modeBadge) {
        const isLive = data.mode === 'live';
        dom.modeBadge.textContent = isLive ? 'Статусы из системы' : 'История на этом устройстве';
        dom.modeBadge.className = `coupon-badge ${isLive ? 'coupon-badge--live' : 'coupon-badge--local'}`;
    }

    if (dom.rankTitle) {
        dom.rankTitle.textContent = translateRank(data.rank?.current || 'Observer');
    }

    if (dom.rankHint) {
        dom.rankHint.textContent = data.rank?.next
            ? `До уровня ${translateRank(data.rank.next.name)} осталось ${formatNumber(data.rank.next.remaining_prizm)} PRIZM оборота.`
            : 'Максимальный уровень кабинета уже достигнут.';
    }

    if (dom.stats) {
        dom.stats.innerHTML = `
            ${renderStatCard('Купоны', data.stats?.total_intents || 0, 'Выпущено кодов')}
            ${renderStatCard('Ждут', data.stats?.waiting_payment || 0, 'Ожидают перевод')}
            ${renderStatCard('Приняты', data.stats?.accepted || 0, 'Подтверждены системой')}
            ${renderStatCard('Отклонены', data.stats?.rejected || 0, 'Не прошли проверку')}
            ${renderStatCard('Выиграли', data.stats?.won || 0, 'Рассчитаны как выигрыш')}
            ${renderStatCard('Оборот', `${formatNumber(data.stats?.turnover_prizm || 0)} PZM`, 'Учтённый объём ставок')}
        `;
    }
}

function renderFeed(items) {
    if (!dom.feed) return;
    if (!items.length) {
        dom.feed.innerHTML = previewMarkup('После первого купона здесь появятся коды, статусы, расчёт и история по вашему кошельку.');
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
        dom.modeBadge.textContent = 'История на этом устройстве';
        dom.modeBadge.className = 'coupon-badge coupon-badge--local';
    }
    if (dom.rankTitle) dom.rankTitle.textContent = 'Старт';
    if (dom.rankHint) dom.rankHint.textContent = 'Кабинет наполнится после выпуска первого кода ставки.';
    if (dom.stats) dom.stats.innerHTML = '';
    if (dom.feed) dom.feed.innerHTML = previewMarkup(message);
}

function previewMarkup(message) {
    return `
        <div class="cabinet-empty">
            <strong>Кабинет появится после первого купона.</strong>
            <div class="cabinet-empty-copy">${escapeHtml(message)}</div>
            <div class="cabinet-preview">
                <div class="cabinet-preview-item"><span>Код ставки</span><span>ожидает перевод</span></div>
                <div class="cabinet-preview-item"><span>Принятие</span><span>после проверки перевода</span></div>
                <div class="cabinet-preview-item"><span>Расчёт</span><span>win, loss или отклонение</span></div>
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
    return RANK_LABELS[rank] || rank || 'Старт';
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
