/**
 * PrizmBet v3 - UI Module
 */
import { escapeHtml, getCountdownText, isMatchImminent } from './utils.js';
import { getFavorites } from './storage.js';
import { getMatchGame, getMatchSport } from './filters.js';

function markStatReady(element) {
    element?.closest('.stat-card')?.classList.remove('stat-card--loading');
}

export function updateStats(matches) {
    const totalMatches = document.getElementById('totalMatches');
    const totalLeagues = document.getElementById('totalLeagues');
    const avgOdds = document.getElementById('avgOdds');
    const heroStats = document.getElementById('heroStatsBar');

    if (totalMatches) {
        totalMatches.textContent = String(matches.length);
        markStatReady(totalMatches);
    }

    if (totalLeagues) {
        totalLeagues.textContent = String(new Set(matches.map((match) => match.league || 'Без лиги')).size);
        markStatReady(totalLeagues);
    }

    if (avgOdds) {
        if (!matches.length) {
            avgOdds.textContent = '—';
        } else {
            const avg = matches.reduce((sum, match) => sum + ((parseFloat(match.p1) || 0) + (parseFloat(match.p2) || 0)) / 2, 0) / matches.length;
            avgOdds.textContent = avg.toFixed(2);
        }
        markStatReady(avgOdds);
    }

    heroStats?.classList.add('stats-bar--ready');
}

export function buildGameFilter(matches) {
    const select = document.getElementById('gameFilter');
    if (!select) return;

    const games = Array.from(new Set(matches.map((match) => getMatchGame(match)))).sort((a, b) => a.localeCompare(b, 'ru'));
    const previousValue = select.value || 'all';
    select.innerHTML = '<option value="all">Все лиги</option>' + games.map((game) => {
        const safeGame = escapeHtml(game);
        return `<option value="${safeGame}">${safeGame}</option>`;
    }).join('');
    select.value = (previousValue === 'all' || games.includes(previousValue)) ? previousValue : 'all';
}

function buildOddButton(label, value, match, teams, dateTimeText) {
    const raw = value || '';
    const unavailable = !raw || raw === '—' || raw === '-' || raw === '0.00' || parseFloat(raw) < 1.01;
    const visibleValue = escapeHtml(unavailable ? '—' : raw);
    if (unavailable) {
        return `<div class="odd-item odd-item--na" data-bet="${label}"><div class="odd-label">${label}</div><div class="odd-value">${visibleValue}</div></div>`;
    }

    const league = escapeHtml(match.league || '');
    const teamsJs = teams.replace(/'/g, "\\'");
    const leagueJs = league.replace(/'/g, "\\'");
    return `<div class="odd-item" data-bet="${label}" onclick="if(navigator.vibrate)navigator.vibrate(20);window.openBetSlip('${match.id}','${teamsJs}','${label}','${visibleValue}','${dateTimeText}','${leagueJs}')"><div class="odd-label">${label}</div><div class="odd-value">${visibleValue}</div></div>`;
}

function buildResultCard(match, isFavorite) {
    const team1 = escapeHtml(match.team1 || match.home_team || '');
    const team2 = escapeHtml(match.team2 || match.away_team || '');
    let score1 = '-';
    let score2 = '-';

    if (String(match.score || '').includes(':')) {
        [score1, score2] = String(match.score).split(':').map((part) => part.trim());
    } else if (String(match.score || '').includes('-')) {
        [score1, score2] = String(match.score).split('-').map((part) => part.trim());
    } else if (match.score) {
        score1 = String(match.score);
        score2 = '';
    }

    const dateText = match.date || (match.match_time ? new Date(match.match_time).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow' }) : '');
    const timeText = match.time || (match.match_time ? new Date(match.match_time).toLocaleTimeString('ru-RU', { timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit' }) : '');

    const card = document.createElement('div');
    card.id = `match-${match.id || ''}`;
    card.className = `match-result-card${isFavorite ? ' favorited' : ''}`;
    card.innerHTML = `
        <div class="result-header">${escapeHtml(match.league || '')}, ${escapeHtml(dateText)} ${escapeHtml(timeText)}</div>
        <div class="result-body">
            <div class="team-block home">
                <div class="team-name">${team1}</div>
                <div class="team-logo">${team1.substring(0, 2).toUpperCase()}</div>
            </div>
            <div class="score-block">
                <div class="score-row">
                    <div class="score-box">${escapeHtml(score1)}</div>
                    <div class="score-box">${escapeHtml(score2)}</div>
                </div>
                <div class="match-status-text">Завершён</div>
            </div>
            <div class="team-block away">
                <div class="team-logo">${team2.substring(0, 2).toUpperCase()}</div>
                <div class="team-name">${team2}</div>
            </div>
        </div>
    `;
    return card;
}

export function createMatchCard(match, favorites) {
    const matchId = match.id || '';
    const isFavorite = favorites.includes(match.id);

    if (match.score) {
        return buildResultCard(match, isFavorite);
    }

    const team1 = escapeHtml(match.team1 || match.home_team || '');
    const team2 = escapeHtml(match.team2 || match.away_team || '');
    const teams = `${team1} vs ${team2}`;
    const shortId = String(matchId).replace(/^[a-z]+_/i, '').slice(-6);
    const countdown = getCountdownText(match);
    const imminent = isMatchImminent(match, 15);
    const dateText = match.date || (match.match_time ? new Date(match.match_time).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow', day: 'numeric', month: 'short' }) : 'Сегодня');
    const timeText = match.time || (match.match_time ? new Date(match.match_time).toLocaleTimeString('ru-RU', { timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit' }) : '');
    const dateTimeText = escapeHtml(`${dateText} ${timeText}`.trim());
    const sport = getMatchSport(match);
    const countdownClasses = ['countdown'];
    if (countdown === 'LIVE') countdownClasses.push('live-badge');
    if (imminent) countdownClasses.push('countdown--imminent');

    const card = document.createElement('div');
    card.id = `match-${matchId}`;
    card.className = `match-card${isFavorite ? ' favorited' : ''}${imminent ? ' match-card--imminent' : ''}`;
    card.innerHTML = `
        <div class="match-header">
            <a class="match-id" href="#match-${matchId}" onclick="window.shareMatch('${matchId}');return false;" title="ID: ${matchId}">#${shortId}</a>
            <div class="match-actions">
                <button class="share-btn" onclick="window.shareMatch('${matchId}')" title="Поделиться матчем">🔗</button>
                <button class="favorite-btn ${isFavorite ? 'active' : ''}" onclick="window.toggleFavorite('${matchId}')" title="${isFavorite ? 'Убрать из избранного' : 'В избранное'}">★</button>
            </div>
        </div>
        <div class="match-time">
            ${dateTimeText}
            ${countdown ? `<span class="${countdownClasses.join(' ')}">${countdown}</span>` : ''}
            ${imminent ? '<span class="match-imminent-badge">Старт < 15 мин</span>' : ''}
        </div>
        <div class="match-teams">${team1} <span class="vs">—</span> ${team2}</div>
        <div class="odds-container">
            <div class="odds-section-title">Основные</div>
            ${buildOddButton('П1', match.p1 || match.odds_home, match, teams, dateTimeText)}
            ${buildOddButton('X', match.x || match.odds_draw, match, teams, dateTimeText)}
            ${buildOddButton('П2', match.p2 || match.odds_away, match, teams, dateTimeText)}
            ${sport === 'football' ? `<div class="odds-section-title">Двойной шанс</div>${buildOddButton('1X', match.p1x, match, teams, dateTimeText)}${buildOddButton('12', match.p12, match, teams, dateTimeText)}${buildOddButton('X2', match.px2, match, teams, dateTimeText)}` : ''}
            ${(match.total_over && match.total_over !== '0.00' && match.total_value) ? `<div class="odds-section-title">Тотал (${match.total_value})</div>${buildOddButton(`ТБ ${match.total_value}`, match.total_over, match, teams, dateTimeText)}${buildOddButton(`ТМ ${match.total_value}`, match.total_under, match, teams, dateTimeText)}<div></div>` : ''}
        </div>
    `;

    return card;
}

export function patchCardOdds(card, match, favorites) {
    const isFavorite = favorites.includes(match.id);
    const imminent = isMatchImminent(match, 15);

    card.classList.toggle('favorited', isFavorite);
    card.classList.toggle('match-card--imminent', imminent);

    const favoriteButton = card.querySelector('.favorite-btn');
    if (favoriteButton) {
        favoriteButton.classList.toggle('active', isFavorite);
        favoriteButton.title = isFavorite ? 'Убрать из избранного' : 'В избранное';
    }

    const oddMap = {
        'П1': match.p1 || match.odds_home,
        'X': match.x || match.odds_draw,
        'П2': match.p2 || match.odds_away,
        '1X': match.p1x,
        '12': match.p12,
        'X2': match.px2,
        [`ТБ ${match.total_value}`]: match.total_over,
        [`ТМ ${match.total_value}`]: match.total_under,
    };

    card.querySelectorAll('[data-bet]').forEach((button) => {
        const betType = button.getAttribute('data-bet');
        const nextRaw = oddMap[betType] || '';
        const unavailable = !nextRaw || nextRaw === '—' || nextRaw === '-' || nextRaw === '0.00' || parseFloat(nextRaw) < 1.01;
        const nextValue = unavailable ? '—' : String(nextRaw);
        const valueElement = button.querySelector('.odd-value');
        if (!valueElement) return;

        if (valueElement.textContent !== nextValue) {
            valueElement.textContent = nextValue;
            valueElement.classList.remove('odd-changed');
            void valueElement.offsetWidth;
            valueElement.classList.add('odd-changed');
            setTimeout(() => valueElement.classList.remove('odd-changed'), 900);
        }

        if (unavailable) {
            button.onclick = null;
            button.className = 'odd-item odd-item--na';
            return;
        }

        const team1 = escapeHtml(match.team1 || match.home_team || '');
        const team2 = escapeHtml(match.team2 || match.away_team || '');
        const teams = `${team1} vs ${team2}`;
        const dateText = match.date || (match.match_time ? new Date(match.match_time).toLocaleDateString('ru-RU') : 'Сегодня');
        const timeText = match.time || (match.match_time ? new Date(match.match_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : '');
        const league = escapeHtml(match.league || '');
        button.onclick = () => window.openBetSlip(match.id || '', teams, betType, nextValue, escapeHtml(`${dateText} ${timeText}`), league);
        button.className = 'odd-item';
    });
}

const LEAGUES_PER_PAGE = 6;
let observer = null;

function renderLeagueChunk(container, pendingLeagues, matchesMap, favorites) {
    const chunk = pendingLeagues.splice(0, LEAGUES_PER_PAGE);
    chunk.forEach((league) => {
        const section = document.createElement('div');
        section.className = 'section';
        section.innerHTML = `<h2 class="section-title">${escapeHtml(league)}</h2>`;
        (matchesMap[league] || []).forEach((match) => section.appendChild(createMatchCard(match, favorites)));
        container.appendChild(section);
    });

    if (pendingLeagues.length > 0) {
        attachSentinel(container, pendingLeagues, matchesMap);
    }
}

function attachSentinel(container, pendingLeagues, matchesMap) {
    if (observer) {
        observer.disconnect();
        observer = null;
    }

    const sentinel = document.createElement('div');
    sentinel.id = 'load-more-sentinel';
    sentinel.style.cssText = 'height:1px;width:100%;pointer-events:none;';
    container.appendChild(sentinel);

    observer = new IntersectionObserver((entries) => {
        if (!entries[0].isIntersecting) return;
        observer.disconnect();
        observer = null;
        sentinel.remove();
        renderLeagueChunk(container, pendingLeagues, matchesMap, getFavorites());
    }, { rootMargin: '400px' });

    observer.observe(sentinel);
}

export function renderMatches(matches) {
    const container = document.getElementById('content');
    if (!container) return;

    if (observer) {
        observer.disconnect();
        observer = null;
    }

    if (!matches.length) {
        container.innerHTML = '<div class="section"><p style="text-align:center; color:var(--text-tertiary);">Матчи не найдены</p></div>';
        return;
    }

    const favorites = getFavorites();
    const matchesMap = {};
    const leagueOrder = [];

    matches.forEach((match) => {
        const league = match.league || 'Без лиги';
        if (!matchesMap[league]) {
            matchesMap[league] = [];
            leagueOrder.push(league);
        }
        matchesMap[league].push(match);
    });

    container.innerHTML = '';

    const hash = window.location.hash;
    const anchorId = hash && hash.startsWith('#match-') ? hash.slice(1) : null;

    if (anchorId) {
        leagueOrder.forEach((league) => {
            const section = document.createElement('div');
            section.className = 'section';
            section.innerHTML = `<h2 class="section-title">${escapeHtml(league)}</h2>`;
            (matchesMap[league] || []).forEach((match) => section.appendChild(createMatchCard(match, favorites)));
            container.appendChild(section);
        });

        requestAnimationFrame(() => {
            const anchor = document.getElementById(anchorId);
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
        return;
    }

    renderLeagueChunk(container, leagueOrder, matchesMap, favorites);
}
