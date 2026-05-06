/**
 * 1PrizmBet - Storage Module
 */

const FAVORITES_KEY = 'one_prizmbet_favorites';
const DETAILS_KEY = 'one_prizmbet_fav_details';
const HISTORY_KEY = 'one_prizmbet_history';
const INTENTS_KEY = 'one_prizmbet_intent_records_v1';
const WALLET_KEY = 'one_prizmbet_wallet_v1';

function readJson(key, fallback) {
    try {
        const raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : fallback;
    } catch {
        return fallback;
    }
}

function writeJson(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
}

// Favorites
export function getFavorites() {
    return readJson(FAVORITES_KEY, []);
}

export function saveFavorites(favorites) {
    writeJson(FAVORITES_KEY, favorites);
}

export function getFavDetails() {
    return readJson(DETAILS_KEY, {});
}

export function saveFavDetails(details) {
    writeJson(DETAILS_KEY, details);
}

// Legacy history
export function getHistory() {
    return readJson(HISTORY_KEY, []);
}

export function saveBetToHistory(betItem) {
    const history = getHistory();
    history.unshift(betItem);
    if (history.length > 50) history.length = 50;
    writeJson(HISTORY_KEY, history);
}

// Wallet
export function getWalletAddress() {
    return String(localStorage.getItem(WALLET_KEY) || '').trim().toUpperCase();
}

export function saveWalletAddress(wallet) {
    localStorage.setItem(WALLET_KEY, String(wallet || '').trim().toUpperCase());
}

// Smart coupon intents
export function getIntentRecords() {
    return readJson(INTENTS_KEY, []);
}

export function upsertIntentRecord(record) {
    if (!record || !record.intent_hash) return;
    const records = getIntentRecords();
    const index = records.findIndex((item) => item.intent_hash === record.intent_hash);
    if (index >= 0) {
        records[index] = record;
    } else {
        records.unshift(record);
    }
    if (records.length > 80) records.length = 80;
    writeJson(INTENTS_KEY, records);
}

export function clearIntentRecords() {
    localStorage.removeItem(INTENTS_KEY);
}
