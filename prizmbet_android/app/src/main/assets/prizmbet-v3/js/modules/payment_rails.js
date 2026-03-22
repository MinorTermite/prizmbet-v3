import { getLanguage } from './i18n.js';

const STORAGE_KEY = 'prizmbet_payment_rail_v1';
const EMPTY_QR = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320"><rect width="320" height="320" rx="28" fill="%230c0c16"/><rect x="22" y="22" width="276" height="276" rx="24" fill="%23141422" stroke="%23363756" stroke-width="2"/><text x="160" y="134" fill="%23b8bfdc" font-family="Arial,sans-serif" font-size="30" text-anchor="middle">RAIL</text><text x="160" y="172" fill="%235e678a" font-family="Arial,sans-serif" font-size="18" text-anchor="middle">QR pending</text></svg>';

const DEFAULT_RAILS = [
    { key: 'prizm', code: 'PRIZM', chain: 'PRIZM', mode: 'auto', settlementCurrency: 'PRIZM', wallet: 'PRIZM-4N7T-L2A7-RQZA-5BETW', qr: 'qr_wallet.webp' },
    { key: 'btc', code: 'BTC', chain: 'Bitcoin', mode: 'pending', settlementCurrency: 'PRIZM', wallet: '', qr: '' },
    { key: 'eth', code: 'ETH', chain: 'Ethereum', mode: 'pending', settlementCurrency: 'PRIZM', wallet: '', qr: '' },
    { key: 'usdt-trc20', code: 'USDT', chain: 'TRON (TRC20)', mode: 'manual', settlementCurrency: 'PRIZM', wallet: '', qr: '' },
    { key: 'usdt-erc20', code: 'USDT', chain: 'Ethereum (ERC20)', mode: 'pending', settlementCurrency: 'PRIZM', wallet: '', qr: '' },
    { key: 'sol', code: 'SOL', chain: 'Solana', mode: 'pending', settlementCurrency: 'PRIZM', wallet: '', qr: '' },
];

const TEXT = {
    copyMissing: 'No address is assigned for this rail yet.',
    copyDone: 'Address copied.',
    copyButton: 'Copy address',
    auto: 'Auto accept',
    manual: 'Manual review',
    pending: 'Pending',
    noAddress: 'Address not assigned yet',
    projectAddress: 'Project address',
    railAutoNote: 'This rail is connected to automatic prematch acceptance. Coupon and status work without manual approval.',
    railManualNote: 'This rail is visible in the interface, but transfers on it still require operator confirmation. PRIZM remains the automatic release flow.',
    railPendingNote: 'This rail is already in the site config. Add a real address and a listener later to activate it without rewriting the coupon.',
    transferManual: 'The bet code is already issued. This rail still requires manual operator confirmation before funds are matched to the coupon.',
    transferPending: 'This rail is already prepared as a payment rail, but it is not active for bet acceptance yet. Use PRIZM for automatic status updates.',
    couponRailAuto: 'This rail works in automatic prematch mode.',
    couponRailManual: 'This rail still requires manual operator confirmation.',
    couponRailPending: 'This rail is not active yet.',
};

function interpolate(template, vars = {}) {
    return String(template || '').replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? ''));
}

function normalizeWindowRails() {
    if (!Array.isArray(window.PRIZMBET_PAYMENT_RAILS)) return [];
    return window.PRIZMBET_PAYMENT_RAILS.filter(Boolean).map((rail) => ({
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
    window.dispatchEvent(new CustomEvent('prizmbet:payment-rail-changed', { detail: { rail: next } }));
    return next;
}

export function getRailAddress(rail = getActiveRail()) {
    return String(rail?.wallet || '').trim();
}

export function getCopyMissingMessage() {
    return TEXT.copyMissing;
}

export function getCopyDoneMessage() {
    return TEXT.copyDone;
}

export function getTransferInstruction({ amountPrizm, code } = {}) {
    const rail = getActiveRail();
    if (rail.mode === 'manual') return TEXT.transferManual;
    if (rail.mode === 'pending') return TEXT.transferPending;
    const amount = Number(amountPrizm || 0).toLocaleString(getLanguage() === 'en' ? 'en-US' : 'ru-RU');
    return `Send ${amount} PRIZM to ${getRailAddress(rail)}. Put code ${code || ''} into the transfer message.`;
}

export function getTransferChipText() {
    const rail = getActiveRail();
    if (rail.mode === 'manual') return `Manual rail: ${rail.code} / ${rail.chain}`;
    if (rail.mode === 'pending') return `Pending rail: ${rail.code} / ${rail.chain}`;
    return `Auto: ${rail.code} / ${rail.chain} ? ${getRailAddress(rail)}`;
}

export function getCouponRailHint() {
    const rail = getActiveRail();
    if (rail.mode === 'manual') return TEXT.couponRailManual;
    if (rail.mode === 'pending') return TEXT.couponRailPending;
    return TEXT.couponRailAuto;
}

function getRailModeLabel(rail) {
    if (rail.mode === 'manual') return TEXT.manual;
    if (rail.mode === 'pending') return TEXT.pending;
    return TEXT.auto;
}

function getRailNote(rail) {
    if (rail.mode === 'manual') return TEXT.railManualNote;
    if (rail.mode === 'pending') return TEXT.railPendingNote;
    return TEXT.railAutoNote;
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
    if (walletLabel) walletLabel.textContent = `${TEXT.projectAddress} ? ${rail.code}`;

    const walletAddress = document.getElementById('walletAddress');
    if (walletAddress) walletAddress.textContent = getRailAddress(rail) || TEXT.noAddress;

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
        if (label) label.textContent = TEXT.copyButton;
    }

    const chip = document.getElementById('bsTransferRailChip');
    if (chip) chip.textContent = getTransferChipText();

    const tip = document.getElementById('bsTransferRailTip');
    if (tip) tip.textContent = getCouponRailHint();
}

export function initPaymentRails() {
    renderPaymentRailUI();
    window.removeEventListener('prizmbet:language-changed', renderPaymentRailUI);
    window.addEventListener('prizmbet:language-changed', renderPaymentRailUI);
}
