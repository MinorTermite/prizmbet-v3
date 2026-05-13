/**
 * PrizmBet v2 - Filters Module
 */
import { parseMatchDateTime } from './utils.js';
import { getFavorites } from './storage.js';

export let currentSportFilter = 'football';
export let currentGameFilter = 'all';
export let currentSort = 'none';
export let currentDateFilter = 'all'; // 'all' | 'today' | 'tomorrow' | 'later'

export const LEAGUE_PRIORITY = {
    'лига чемпионов уэфа': 1, 'champions league': 1, 'лч': 1,
    'лига европы уэфа': 2, 'europa league': 2, 'ле': 2,
    'премьер-лига': 3, 'premier league': 3, 'эпл': 3,
    'ла лига': 4, 'la liga': 4, 'серия а': 5, 'бундеслига': 6,
    'лига 1': 7, 'рпл': 8, 'rpl': 8,
    'кхл': 10, 'khl': 10, 'nhl': 11, 'нхл': 11,
    'nba': 20, 'нба': 20,
};

export function inferSport(match) {
    const t = ((match.league || '') + ' ' + (match.team1 || '') + ' ' + (match.team2 || '')).toLowerCase();
    if (/настольный теннис|наст\. теннис|table tennis/.test(t)) return 'tabletennis';
    if (/dota|counter-strike|cs2|valorant|league of legends|lol|rocket league|rlcs|pubg|apex|rainbow six|overwatch/.test(t)) return 'esports';
    if (/кхл|нхл|hockey|nhl|ahl|shl|liiga|del|хоккей/.test(t)) return 'hockey';
    if (/nba|нба|баскет|euroleague|евролига|vtb|acb|bbl/.test(t)) return 'basket';
    if (/теннис|atp|wta|itf|уимблдон|ролан гаррос|tennis/.test(t)) return 'tennis';
    if (/волейбол|volleyball|cev|vnl|суперлига|plusliga|superlega/.test(t)) return 'volleyball';
    if (/ufc|bellator|mma|one championship|pfl|acb mma/.test(t)) return 'mma';
    return 'football';
}

export function getMatchSport(match) {
    return (match.sport || '').toLowerCase() || inferSport(match);
}

export function getMatchGame(m) {
    if (m.game) return String(m.game);
    const l = (m.league || '').toLowerCase();
    if (l.includes('лига чемпионов') || l.includes('champions league')) return 'ЛЧ УЕФА';
    if (l.includes('лига европы') || l.includes('europa league')) return 'ЛЕ УЕФА';
    if (l.includes('премьер-лига') && l.includes('англия')) return 'Англия. Премьер-лига';
    if (l.includes('ла лига') || l.includes('la liga')) return 'Испания. Ла Лига';
    if (l.includes('бундеслига')) return 'Германия. Бундеслига';
    if (l.includes('серия a') || l.includes('serie a')) return 'Италия. Серия A';
    if (l.includes('кхл')) return 'КХЛ';
    if (l.includes('нхл') || l.includes('nhl')) return 'НХЛ';
    if (l.includes('nba') || l.includes('нба')) return 'NBA';
    return m.league || 'Другое';
}

export function isValidMatch(m) {
    const team1 = (m.team1 || '').trim();
    const team2 = (m.team2 || '').trim();
    if (!team1 || !team2) return false;
    if (/^(1|x|12|x2|2|0|-)$/i.test(team2)) return false;
    if (team2.length < 2) return false;
    return true;
}

export function getFilterState() {
    return {
        sport: currentSportFilter,
        league: currentGameFilter,
        sort: currentSort,
        date: currentDateFilter,
        search: document.getElementById('searchInput')?.value || '',
        popularOnly: document.getElementById('popularOnly')?.checked || false
    };
}

export function filterMatches(matches, state) {
    const now = new Date();
    // Date boundaries (local midnight)
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const todayEnd   = new Date(todayStart.getTime() + 86400000);
    const tomorrowEnd = new Date(todayEnd.getTime() + 86400000);

    const favIds = state.sport === 'favs' ? getFavorites() : null;

    return matches.filter(m => {
        if (!isValidMatch(m)) return false;

        // Favorites tab
        if (favIds !== null) {
            return favIds.includes(m.id);
        }

        // Sport filter
        const mSport = getMatchSport(m);
        if (state.sport === 'totals') {
            // Totals tab: show any sport match that has total odds
            if (!m.total_over || m.total_over === '—' || m.total_over === '0.00') return false;
        } else if (state.sport !== 'all' && state.sport !== 'results' && mSport !== state.sport) {
            return false;
        }

        const start = parseMatchDateTime(m);
        const diffMs = now - start;

        // Results tab — show only scored matches, skip remaining filters
        if (state.sport === 'results') return !!m.score;

        // Hide ALL scored matches from main list (they belong in Results tab)
        if (m.score) return false;

        // Hide matches without score that started more than 8h ago.
        // 8h threshold matches the workflow update interval (3x/day ≈ every 8h),
        // so matches don't disappear between scheduled data refreshes.
        if (diffMs > (8 * 60 * 60 * 1000)) return false;

        // Date filter
        if (state.date !== 'all') {
            const t = start.getTime();
            if (state.date === 'today'    && (t < todayStart.getTime() || t >= todayEnd.getTime()))   return false;
            if (state.date === 'tomorrow' && (t < todayEnd.getTime()   || t >= tomorrowEnd.getTime())) return false;
            if (state.date === 'later'    &&  t < tomorrowEnd.getTime())                               return false;
        }

        // League filter
        const mLeagueGroup = getMatchGame(m);
        if (state.league !== 'all' && mLeagueGroup !== state.league) return false;

        // Popular only — require both p1 and p2 odds to be set and > 1
        if (state.popularOnly) {
            const p1 = parseFloat(m.p1 || m.odds_home);
            const p2 = parseFloat(m.p2 || m.odds_away);
            if (!p1 || !p2 || p1 <= 1 || p2 <= 1) return false;
        }

        // Search filter
        if (state.search) {
            const s = state.search.toLowerCase();
            const content = `${m.home_team || m.team1} ${m.away_team || m.team2} ${m.league} ${m.id}`.toLowerCase();
            if (!content.includes(s)) return false;
        }

        return true;
    });
}

export function getLeaguePriority(match) {
    const league = (match.league || "").toLowerCase();
    for (const [key, priority] of Object.entries(LEAGUE_PRIORITY)) {
        if (league.includes(key)) return priority;
    }
    return 999;
}

export function sortMatches(matches, sortType) {
    const sorted = [...matches];
    const now = new Date();
    
    function isPast(m) {
        const start = parseMatchDateTime(m);
        const diffMs = now - start;
        if (m.score && diffMs > (3 * 60 * 60 * 1000)) return true;
        if (diffMs > (8 * 60 * 60 * 1000)) return true;
        return false;
    }

    sorted.sort((a, b) => {
        const pastA = isPast(a);
        const pastB = isPast(b);
        
        // Put past matches at the bottom
        if (pastA !== pastB) return pastA ? 1 : -1;
        
        if (sortType === 'time') {
            return parseMatchDateTime(a) - parseMatchDateTime(b);
        } else if (sortType === 'odds') {
            return (parseFloat(a.odds_home || a.p1) || 0) - (parseFloat(b.odds_home || b.p1) || 0);
        } else if (sortType === 'league') {
            const pa = getLeaguePriority(a);
            const pb = getLeaguePriority(b);
            if (pa !== pb) return pa - pb;
            return (a.league || "").localeCompare(b.league || "");
        }
        return 0;
    });
    return sorted;
}

// State setters
export function setSportFilter(val) { currentSportFilter = val; }
export function setGameFilter(val) { currentGameFilter = val; }
export function setSort(val) { currentSort = val; }
export function setDateFilter(val) { currentDateFilter = val; }
