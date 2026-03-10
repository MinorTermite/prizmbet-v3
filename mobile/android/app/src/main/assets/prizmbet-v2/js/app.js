/**
 * PrizmBet v2 - Main Entry Point
 */
import * as utils from './modules/utils.js';
import * as filters from './modules/filters.js';
import * as storage from './modules/storage.js';
import * as notif from './modules/notifications.js';
import * as betSlip from './modules/bet_slip.js';
import * as historyUI from './modules/history_ui.js';
import * as ui from './modules/ui.js';

// Global matches buffer (shared from api.js)
let allMatches = [];

/**
 * Main Orchestration Logic
 */
function updateApp(newMatches) {
    if (Array.isArray(newMatches)) {
        window.__ALL_MATCHES__ = newMatches;
    }
    allMatches = window.__ALL_MATCHES__ || [];
    
    // 1. Check notifications
    notif.checkFinishedFavorites(allMatches);

    // 2. Filter & Sort
    const state = filters.getFilterState();
    let filtered = filters.filterMatches(allMatches, state);
    filtered = filters.sortMatches(filtered, state.sort);
    
    // 3. Render — league filter should only show leagues for the active sport
    const sportFiltered = filters.filterMatches(allMatches, { ...state, league: 'all' });
    ui.buildGameFilter(sportFiltered);
    ui.updateStats(filtered);
    ui.renderMatches(filtered);
}

/**
 * Global Exposure for HTML inline handlers
 */
Object.assign(window, {
    // UI Helpers
    shareMatch: (id) => utils.shareMatch(id, notif.showToast),
    
    // Favorites
    toggleFavorite: (id) => {
        let favs = storage.getFavorites();
        const index = favs.indexOf(id);
        if (index > -1) {
            favs.splice(index, 1);
        } else {
            favs.push(id);
            // Detailed fav info for notifications
            const match = allMatches.find(m => m.id === id);
            if (match) {
                let details = storage.getFavDetails();
                details[id] = { 
                    home: match.home_team || match.team1 || 'Команда 1', 
                    away: match.away_team || match.team2 || 'Команда 2', 
                    time: match.match_time 
                };
                storage.saveFavDetails(details);
            }
        }
        storage.saveFavorites(favs);
        notif.showToast(index > -1 ? 'Удалено из избранного' : 'Добавлено в избранное');
        updateApp();
    },

    // Notifications
    requestNotificationPermission: async () => {
        const granted = await notif.requestNotificationPermission();
        if (granted) notif.showToast('Уведомления включены!');
        notif.updateNotifBell();
    },

    // Bet Slip
    openBetSlip: (id, teams, betType, coef, datetime, league) => {
        const betData = { id, teams, betType, coef, datetime, league };
        betSlip.openBetSlip(betData, betType, coef);
    },
    closeBetSlip: betSlip.closeBetSlip,
    calcPayout: betSlip.calcPayout,
    copyBetSlipData: betSlip.copyBetSlipData,
    toggleMyBets: betSlip.toggleMyBets,
    checkMyBets: betSlip.checkMyBets,
    copyWallet: (btn) => betSlip.copyWallet(btn),

    // Helpers
    openImage: (src) => window.open(src, '_blank'),

    // History
    openHistory: historyUI.openHistory,
    closeHistory: historyUI.closeHistory,
    clearHistory: historyUI.clearHistory,

    // Orchestrator
    renderMatches: updateApp,
    onSearchInput: updateApp,
    // Manual refresh always loads full matches.json to get fresh / all-dates data
    refreshData: () => { if (window.loadData) window.loadData('full').then(updateApp); }
});

/**
 * Event Listeners
 */
function wireFilters() {
    // Tabs
    document.querySelectorAll('.tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filters.setSportFilter(btn.dataset.sport);
            updateApp();
        });
    });

    // League select
    document.getElementById('gameFilter')?.addEventListener('change', e => {
        filters.setGameFilter(e.target.value);
        updateApp();
    });

    // Sort buttons (only .sort-only, not date buttons)
    document.querySelectorAll('.sort-only').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.sort-only').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filters.setSort(btn.dataset.sort);
            updateApp();
        });
    });

    // Date filter buttons
    document.querySelectorAll('.date-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.date-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filters.setDateFilter(btn.dataset.date);
            // 'later' needs full data (matches-today.json only has today+tomorrow)
            if (btn.dataset.date === 'later' && window.loadData) {
                window.loadData('full').then(updateApp);
            } else {
                updateApp();
            }
        });
    });

    // Popular only checkbox
    document.getElementById('popularOnly')?.addEventListener('change', updateApp);
}

/**
 * Initialization
 */
window.addEventListener('load', () => {
    utils.initScrollProgress();
    utils.initTabsHint();
    notif.updateNotifBell();
    wireFilters();

    // Custom event from modules
    window.addEventListener('betPlaced', e => {
        storage.saveBetToHistory(e.detail);
        notif.showToast('✅ Ставка сохранена в историю');
    });

    // Initial load
    if (window.loadData) {
        window.loadData().then(updateApp);
    }
});

// Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js', { scope: './' })
            .then(reg => {
                // Если есть новая версия SW — обновляем тихо
                reg.addEventListener('updatefound', () => {
                    reg.installing?.addEventListener('statechange', e => {
                        if (e.target.state === 'installed' && navigator.serviceWorker.controller) {
                            // Новый SW готов — уведомим пользователя при желании
                            console.log('[SW] Новая версия готова');
                        }
                    });
                });
            })
            .catch(err => console.warn('[SW] Регистрация не удалась:', err));
    });
}
