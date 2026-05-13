/**
 * PrizmBet v2 - Storage Module
 */

const STORAGE_KEY = 'prizmbet_favorites';
const DETAILS_KEY = 'prizmbet_fav_details';
const HISTORY_KEY = 'prizmbet_history';

// Favorites
export function getFavorites() {
    try {
        return JSON.parse(localStorage.getItem(STORAGE_KEY)) || [];
    } catch { return []; }
}

export function saveFavorites(favorites) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
}

export function getFavDetails() {
    try {
        return JSON.parse(localStorage.getItem(DETAILS_KEY)) || {};
    } catch { return {}; }
}

export function saveFavDetails(details) {
    localStorage.setItem(DETAILS_KEY, JSON.stringify(details));
}

// History
export function getHistory() {
    try {
        return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
    } catch { return []; }
}

export function saveBetToHistory(betItem) {
    const h = getHistory();
    h.unshift(betItem);
    if (h.length > 50) h.pop();
    localStorage.setItem(HISTORY_KEY, JSON.stringify(h));
}
