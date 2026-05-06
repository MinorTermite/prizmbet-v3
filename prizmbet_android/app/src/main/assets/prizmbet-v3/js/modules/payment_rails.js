import { getLanguage } from './i18n.js';

const STORAGE_KEY = 'one_prizmbet_payment_rail_v1';
const EMPTY_QR = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320"><rect width="320" height="320" rx="28" fill="%230c0c16"/><rect x="22" y="22" width="276" height="276" rx="24" fill="%23141422" stroke="%23363756" stroke-width="2"/><text x="160" y="134" fill="%23b8bfdc" font-family="Arial,sans-serif" font-size="30" text-anchor="middle">RAIL</text><text x="160" y="172" fill="%235e678a" font-family="Arial,sans-serif" font-size="18" text-anchor="middle">QR pending</text></svg>';

const DEFAULT_RAILS = [
    { key: 'prizm', code: 'PRIZM', chain: 'PRIZM', mode: 'auto', settlementCurrency: 'PRIZM', wallet: 'PRIZM-FSLA-9FZS-A6SX-3GXNV', qr: 'qr_wallet.webp', minBet: 10, maxBet: 30000 },
    { key: 'usdt-trc20', code: 'USDT', chain: 'TRON (TRC20)', mode: 'auto', settlementCurrency: 'USDT', wallet: '', qr: '', minBet: 5, maxBet: 1000 },
    { key: 'btc', code: 'BTC', chain: 'Bitcoin', mode: 'pending', settlementCurrency: 'BTC', wallet: '', qr: '', minBet: 0, maxBet: 0 },
    { key: 'eth', code: 'ETH', chain: 'Ethereum', mode: 'pending', settlementCurrency: 'ETH', wallet: '', qr: '', minBet: 0, maxBet: 0 },
    { key: 'usdt-erc20', code: 'USDT', chain: 'Ethereum (ERC20)', mode: 'pending', settlementCurrency: 'USDT', wallet: '', qr: '', minBet: 0, maxBet: 0 },
    { key: 'sol', code: 'SOL', chain: 'Solana', mode: 'pending', settlementCurrency: 'SOL', wallet: '', qr: '', minBet: 0, maxBet: 0 },
];

const TEXT = {
    copyMissing: {
        ru: 'Для этого платёжного рельса адрес ещё не задан.',
        en: 'No address is assigned for this rail yet.',
    },
    copyDone: {
        ru: 'Адрес скопирован.',
        en: 'Address copied.',
    },
    copyButton: {
        ru: 'Скопировать адрес',
        en: 'Copy address',
    },
    auto: {
        ru: 'Авто',
        en: 'Auto accept',
    },
    manual: {
        ru: 'Ручной',
        en: 'Manual review',
    },
    pending: {
        ru: 'Ожидает',
        en: 'Pending',
    },
    noAddress: {
        ru: 'Адрес ещё не задан',
        en: 'Address not assigned yet',
    },
    projectAddress: {
        ru: 'Кошелёк проекта',
        en: 'Project address',
    },
    railAutoNote: {
        ru: 'Этот рельс подключён к автоматическому prematch-приёму. Купон и статусы работают без ручного подтверждения.',
        en: 'This rail is connected to automatic prematch acceptance. Coupon and status work without manual approval.',
    },
    railManualNote: {
        ru: 'Этот рельс виден в интерфейсе, но переводы по нему пока требуют ручного подтверждения оператора. Автоматический сценарий остаётся на PRIZM.',
        en: 'This rail is visible in the interface, but transfers on it still require operator confirmation. PRIZM remains the automatic release flow.',
    },
    railPendingNote: {
        ru: 'Этот рельс уже заведён в конфиг сайта. Добавьте реальный адрес и listener позже, чтобы включить его без переписывания купона.',
        en: 'This rail is already in the site config. Add a real address and a listener later to activate it without rewriting the coupon.',
    },
    transferManual: {
        ru: 'Код уже выпущен. Этот платёжный рельс пока требует ручного подтверждения оператора перед привязкой перевода к купону.',
        en: 'The bet code is already issued. This rail still requires manual operator confirmation before funds are matched to the coupon.',
    },
    transferPending: {
        ru: 'Этот платёжный рельс уже подготовлен в конфиге, но ещё не активен для приёма ставок. Для автоматических статусов используйте PRIZM.',
        en: 'This rail is already prepared as a payment rail, but it is not active for bet acceptance yet. Use PRIZM for automatic status updates.',
    },
    couponRailAuto: {
        ru: 'Этот рельс работает в автоматическом prematch-режиме.',
        en: 'This rail works in automatic prematch mode.',
    },
    couponRailManual: {
        ru: 'Этот рельс пока требует ручного подтверждения оператора.',
        en: 'This rail still requires manual operator confirmation.',
    },
    couponRailPending: {
        ru: 'Этот рельс пока не активирован.',
        en: 'This rail is not active yet.',
    },
};

function interpolate(template, vars = {}) {
    return String(template || '').replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? ''));
}

function getText(key, vars = {}) {
    const entry = TEXT[key];
    if (!entry) return '';
    if (typeof entry === 'string') return interpolate(entry, vars);
    const lang = getLanguage() === 'ru' ? 'ru' : 'en';
    return interpolate(entry[lang] || entry.en || entry.ru || '', vars);
}

function normalizeWindowRails() {
    if (!Array.isArray(window.ONE_PRIZMBET_PAYMENT_RAILS)) return [];
    return window.ONE_PRIZMBET_PAYMENT_RAILS.filter(Boolean).map((rail) => ({
        ...rail,
        key: String(rail.key || '').trim().toLowerCase(),
        code: String(rail.code || rail.key || '').trim().toUpperCase(),
        chain: String(rail.chain || rail.code || rail.key || '').trim(),
        mode: ['auto', 'manual', 'pending'].includes(String(rail.mode || '').trim()) ? String(rail.mode).trim() : 'pending',
        settlementCurrency: String(rail.settlementCurrency || 'PRIZM').trim().toUpperCase(),
        wallet: String(rail.wallet || '').trim(),
        qr: String(rail.qr || '').trim(),
    }));
}

function resolveRails() {
    const custom = normalizeWindowRails();
    if (!custom.length) return DEFAULT_RAILS.slice();
    const merged = [];
    const defaultsByKey = new Map(DEFAULT_RAILS.map((item) => [item.key, item]));
    const seen = new Set();
    custom.forEach((item) => {
        if (!item.key) return;
        seen.add(item.key);
        merged.push({ ...(defaultsByKey.get(item.key) || {}), ...item });
    });
    DEFAULT_RAILS.forEach((item) => {
        if (!seen.has(item.key)) merged.push(item);
    });
    return merged;
}

export function getPaymentRails() {
    return resolveRails();
}

export function getActiveRailKey() {
    const rails = getPaymentRails();
    const stored = String(localStorage.getItem(STORAGE_KEY) || '').trim().toLowerCase();
    if (stored && rails.some((item) => item.key === stored)) return stored;
    return rails[0]?.key || 'prizm';
}

export function getActiveRail() {
    const rails = getPaymentRails();
    const key = getActiveRailKey();
    return rails.find((item) => item.key === key) || rails[0] || DEFAULT_RAILS[0];
}

export function setActiveRail(key) {
    const rails = getPaymentRails();
    const next = rails.find((item) => item.key === String(key || '').trim().toLowerCase()) || rails[0] || DEFAULT_RAILS[0];
    localStorage.setItem(STORAGE_KEY, next.key);
    renderPaymentRailUI();
    window.dispatchEvent(new CustomEvent('one-prizmbet:payment-rail-changed', { detail: { rail: next } }));
    return next;
}

export function getRailAddress(rail = getActiveRail()) {
    return String(rail?.wallet || '').trim();
}

export function getCopyMissingMessage() {
    return getText('copyMissing');
}

export function getCopyDoneMessage() {
    return getText('copyDone');
}

export function getTransferInstruction({ amountPrizm, code } = {}) {
    const rail = getActiveRail();
    if (rail.mode === 'manual') return getText('transferManual');
    if (rail.mode === 'pending') return getText('transferPending');
    const amount = Number(amountPrizm || 0).toLocaleString(getLanguage() === 'en' ? 'en-US' : 'ru-RU');
    const currency = rail.code || 'PRIZM';
    if (currency === 'USDT') {
        return getLanguage() === 'ru'
            ? `Отправьте ${amount} USDT (TRC-20) на адрес ${getRailAddress(rail)}. TRON не поддерживает сообщения — ставка привяжется по кошельку.`
            : `Send ${amount} USDT (TRC-20) to ${getRailAddress(rail)}. TRON does not support messages — bet will be matched by wallet.`;
    }
    return getLanguage() === 'ru'
        ? `Отправьте ${amount} ${currency} на адрес ${getRailAddress(rail)}. Вставьте код ${code || ''} в сообщение к переводу.`
        : `Send ${amount} ${currency} to ${getRailAddress(rail)}. Put code ${code || ''} into the transfer message.`;
}

export function getActiveRailCurrency() {
    return getActiveRail()?.settlementCurrency || 'PRIZM';
}

export function getActiveRailLimits() {
    const rail = getActiveRail();
    return { minBet: rail?.minBet || 0, maxBet: rail?.maxBet || 0 };
}

export function getTransferChipText() {
    const rail = getActiveRail();
    if (rail.mode === 'manual') return getLanguage() === 'ru' ? `Ручной рельс: ${rail.code} / ${rail.chain}` : `Manual rail: ${rail.code} / ${rail.chain}`;
    if (rail.mode === 'pending') return getLanguage() === 'ru' ? `Рельс ожидает активации: ${rail.code} / ${rail.chain}` : `Pending rail: ${rail.code} / ${rail.chain}`;
    return getLanguage() === 'ru'
        ? `Авто: ${rail.code} / ${rail.chain} - ${getRailAddress(rail)}`
        : `Auto: ${rail.code} / ${rail.chain} - ${getRailAddress(rail)}`;
}

export function getCouponRailHint() {
    const rail = getActiveRail();
    if (rail.mode === 'manual') return getText('couponRailManual');
    if (rail.mode === 'pending') return getText('couponRailPending');
    return getText('couponRailAuto');
}

function getRailModeLabel(rail) {
    if (rail.mode === 'manual') return getText('manual');
    if (rail.mode === 'pending') return getText('pending');
    return getText('auto');
}

function getRailNote(rail) {
    if (rail.mode === 'manual') return getText('railManualNote');
    if (rail.mode === 'pending') return getText('railPendingNote');
    return getText('railAutoNote');
}

function renderRailButtons(container, activeRail) {
    if (!container) return;
    container.innerHTML = getPaymentRails().map((rail) => `
        <button type="button" class="wallet-rail-btn ${rail.key === activeRail.key ? 'is-active' : ''}" data-rail-key="${rail.key}">
            <span class="wallet-rail-btn__code">${rail.code}</span>
            <span class="wallet-rail-btn__mode wallet-rail-btn__mode--${rail.mode}">${getRailModeLabel(rail)}</span>
        </button>
    `).join('');
    container.querySelectorAll('[data-rail-key]').forEach((button) => {
        button.addEventListener('click', () => setActiveRail(button.dataset.railKey));
    });
}

export function renderPaymentRailUI() {
    const rail = getActiveRail();
    renderRailButtons(document.getElementById('walletRailSwitch'), rail);

    const walletLabel = document.getElementById('walletLabel');
    if (walletLabel) walletLabel.textContent = `${getText('projectAddress')} - ${rail.code}`;

    const walletAddress = document.getElementById('walletAddress');
    if (walletAddress) walletAddress.textContent = getRailAddress(rail) || getText('noAddress');

    const walletChain = document.getElementById('walletRailChain');
    if (walletChain) walletChain.textContent = rail.chain;

    const walletBadge = document.getElementById('walletRailModeBadge');
    if (walletBadge) {
        walletBadge.textContent = getRailModeLabel(rail);
        walletBadge.className = `wallet-rail-badge wallet-rail-badge--${rail.mode}`;
    }

    const walletNote = document.getElementById('walletRailNote');
    if (walletNote) walletNote.textContent = getRailNote(rail);

    const walletQr = document.getElementById('walletQrCode');
    if (walletQr) {
        walletQr.src = rail.qr || EMPTY_QR;
        walletQr.alt = `${rail.code} QR`;
        walletQr.classList.toggle('qr-code--placeholder', !rail.qr);
    }

    const walletCopyBtn = document.getElementById('walletCopyBtn');
    if (walletCopyBtn) {
        walletCopyBtn.disabled = !getRailAddress(rail);
        walletCopyBtn.classList.toggle('is-disabled', !getRailAddress(rail));
        const label = walletCopyBtn.querySelector('[data-wallet-copy-label]');
        if (label) label.textContent = getText('copyButton');
    }

    const chip = document.getElementById('bsTransferRailChip');
    if (chip) chip.textContent = getTransferChipText();

    const tip = document.getElementById('bsTransferRailTip');
    if (tip) tip.textContent = getCouponRailHint();
}

export function initPaymentRails() {
    renderPaymentRailUI();
    window.removeEventListener('one-prizmbet:language-changed', renderPaymentRailUI);
    window.addEventListener('one-prizmbet:language-changed', renderPaymentRailUI);
}
