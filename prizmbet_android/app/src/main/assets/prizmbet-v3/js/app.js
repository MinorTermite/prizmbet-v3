/**
 * PrizmBet v3 - Main Entry Point
 */
import * as utils from './modules/utils.js';
import * as filters from './modules/filters.js';
import * as storage from './modules/storage.js';
import * as notif from './modules/notifications.js';
import * as betSlip from './modules/bet_slip.js';
import * as historyUI from './modules/history_ui.js';
import * as ui from './modules/ui.js';

let allMatches = [];

function getActiveMeta() {
    return window.__MATCHES_META__ || {};
}

function hasTotalMarket(match) {
    return Boolean(match.total_over && match.total_over !== '—' && match.total_over !== '0.00');
}

function getStaleFallbackMatches(matches, state) {
    const favIds = state.sport === 'favs' ? storage.getFavorites() : null;

    return matches.filter((match) => {
        if (!filters.isValidMatch(match)) return false;
        if (favIds !== null) return favIds.includes(match.id);
        if (state.sport === 'results') return Boolean(match.score);
        if (match.score) return false;

        const matchSport = filters.getMatchSport(match);
        if (state.sport === 'totals') {
            if (!hasTotalMarket(match)) return false;
        } else if (state.sport !== 'all' && state.sport !== 'results' && matchSport !== state.sport) {
            return false;
        }

        if (state.league !== 'all' && filters.getMatchGame(match) !== state.league) return false;

        if (state.popularOnly) {
            const p1 = parseFloat(match.p1 || match.odds_home);
            const p2 = parseFloat(match.p2 || match.odds_away);
            if (!p1 || !p2 || p1 <= 1 || p2 <= 1) return false;
        }

        if (state.search) {
            const search = state.search.toLowerCase();
            const content = `${match.home_team || match.team1} ${match.away_team || match.team2} ${match.league} ${match.id}`.toLowerCase();
            if (!content.includes(search)) return false;
        }

        return true;
    }).sort((a, b) => {
        const liveDelta = Number(Boolean(b.is_live)) - Number(Boolean(a.is_live));
        if (liveDelta !== 0) return liveDelta;
        return utils.parseMatchDateTime(a) - utils.parseMatchDateTime(b);
    });
}

function updateApp(newMatches) {
    if (Array.isArray(newMatches)) {
        window.__ALL_MATCHES__ = newMatches;
    }
    allMatches = window.__ALL_MATCHES__ || [];

    notif.checkFinishedFavorites(allMatches);

    const state = filters.getFilterState();
    const meta = getActiveMeta();

    let filtered = filters.filterMatches(allMatches, state);
    filtered = filters.sortMatches(filtered, state.sort);

    let displayMatches = filtered;
    let staleFallback = false;

    if (!filtered.length && allMatches.length && meta.isStale && !state.search) {
        const fallbackMatches = getStaleFallbackMatches(allMatches, state);
        if (fallbackMatches.length) {
            displayMatches = filters.sortMatches(fallbackMatches, state.sort);
            staleFallback = true;
        }
    }

    const gameFilterSource = meta.isStale
        ? getStaleFallbackMatches(allMatches, { ...state, league: 'all', date: 'all', search: '' })
        : filters.filterMatches(allMatches, { ...state, league: 'all' });

    ui.buildGameFilter(gameFilterSource);
    ui.updateStats(displayMatches, { sourceMatches: allMatches, meta, staleFallback });
    ui.renderMatches(displayMatches, { sourceMatches: allMatches, meta, staleFallback });
}

Object.assign(window, {
    shareMatch: (id) => utils.shareMatch(id, notif.showToast),
    toggleFavorite: (id) => {
        const favorites = storage.getFavorites();
        const index = favorites.indexOf(id);
        if (index > -1) {
            favorites.splice(index, 1);
        } else {
            favorites.push(id);
            const match = allMatches.find((item) => item.id === id);
            if (match) {
                const details = storage.getFavDetails();
                details[id] = {
                    home: match.home_team || match.team1 || 'Команда 1',
                    away: match.away_team || match.team2 || 'Команда 2',
                    time: match.match_time,
                };
                storage.saveFavDetails(details);
            }
        }
        storage.saveFavorites(favorites);
        notif.showToast(index > -1 ? 'Удалено из избранного' : 'Добавлено в избранное');
        updateApp();
    },
    requestNotificationPermission: async () => {
        const granted = await notif.requestNotificationPermission();
        if (granted) notif.showToast('Уведомления включены!');
        notif.updateNotifBell();
    },
    openBetSlip: (id, teams, betType, coef, datetime, league) => {
        const betData = { id, teams, betType, coef, datetime, league };
        betSlip.openBetSlip(betData, betType, coef);
    },
    closeBetSlip: betSlip.closeBetSlip,
    calcPayout: betSlip.calcPayout,
    copyBetSlipData: betSlip.copyBetSlipData,
    copyBetSlipCode: betSlip.copyIntentCode,
    refreshSlipStatus: betSlip.refreshSlipStatus,
    toggleMyBets: historyUI.openHistory,
    checkMyBets: historyUI.openHistory,
    copyWallet: (btn) => betSlip.copyWallet(btn),
    openImage: (src) => window.open(src, '_blank'),
    openHistory: historyUI.openHistory,
    closeHistory: historyUI.closeHistory,
    clearHistory: historyUI.clearHistory,
    renderMatches: updateApp,
    onSearchInput: updateApp,
    refreshData: () => {
        if (window.loadData) window.loadData('full').then(updateApp);
    },
});

function wireFilters() {
    document.querySelectorAll('.tab').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach((item) => item.classList.remove('active'));
            btn.classList.add('active');
            filters.setSportFilter(btn.dataset.sport);
            updateApp();
        });
    });

    document.getElementById('gameFilter')?.addEventListener('change', (event) => {
        filters.setGameFilter(event.target.value);
        updateApp();
    });

    document.querySelectorAll('.sort-only').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.sort-only').forEach((item) => item.classList.remove('active'));
            btn.classList.add('active');
            filters.setSort(btn.dataset.sort);
            updateApp();
        });
    });

    document.querySelectorAll('.date-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.date-btn').forEach((item) => item.classList.remove('active'));
            btn.classList.add('active');
            filters.setDateFilter(btn.dataset.date);
            if (btn.dataset.date === 'later' && window.loadData) {
                window.loadData('full').then(updateApp);
            } else {
                updateApp();
            }
        });
    });

    document.getElementById('popularOnly')?.addEventListener('change', updateApp);
}

window.addEventListener('load', () => {
    utils.initScrollProgress();
    utils.initTabsHint();
    notif.updateNotifBell();
    wireFilters();
    betSlip.initSmartBetting();
    historyUI.initHistoryUI();

    if (window.loadData) {
        window.loadData().then(updateApp);
    }
});

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js', { scope: './' })
            .then((registration) => {
                registration.addEventListener('updatefound', () => {
                    registration.installing?.addEventListener('statechange', (event) => {
                        if (event.target.state === 'installed' && navigator.serviceWorker.controller) {
                            console.log('[SW] Новая версия готова');
                        }
                    });
                });
            })
            .catch((error) => console.warn('[SW] Регистрация не удалась:', error));
    });
}
