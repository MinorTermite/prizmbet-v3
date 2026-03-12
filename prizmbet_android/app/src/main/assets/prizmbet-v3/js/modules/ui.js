/**
 * PrizmBet v3 - UI Module
 */
import { escapeHtml, getCountdownText, isMatchImminent, isMatchLive } from './utils.js';
import { getFavorites } from './storage.js';
import { getMatchGame, getMatchSport } from './filters.js';

function markStatReady(element) {
    element?.closest('.stat-card')?.classList.remove('stat-card--loading');
}

export function updateStats(matches, context = {}) {
    const totalMatches = document.getElementById('totalMatches');
    const totalLeagues = document.getElementById('totalLeagues');
    const avgOdds = document.getElementById('avgOdds');
    const heroStats = document.getElementById('heroStatsBar');
    const sourceMatches = Array.isArray(context.sourceMatches) && context.sourceMatches.length ? context.sourceMatches : matches;

    if (totalMatches) {
        totalMatches.textContent = sourceMatches.length ? String(sourceMatches.length) : '—';
        markStatReady(totalMatches);
    }

    if (totalLeagues) {
        totalLeagues.textContent = sourceMatches.length ? String(new Set(sourceMatches.map((match) => match.league || 'Без лиги')).size) : '—';
        markStatReady(totalLeagues);
    }

    if (avgOdds) {
        const validOdds = sourceMatches
            .map((match) => ((parseFloat(match.p1) || 0) + (parseFloat(match.p2) || 0)) / 2)
            .filter((value) => value > 0);

        avgOdds.textContent = validOdds.length
            ? (validOdds.reduce((sum, value) => sum + value, 0) / validOdds.length).toFixed(2)
            : '—';
        markStatReady(avgOdds);
    }

    heroStats?.classList.add('stats-bar--ready');
    heroStats?.classList.toggle('stats-bar--stale', Boolean(context.meta?.isStale));
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

function getExternalMatchUrl(match) {
    const url = String(match.match_url || '').trim();
    return /^https?:\/\//i.test(url) ? url : '';
}

function hasTotalMarket(match) {
    return Boolean(match.total_value && match.total_over && match.total_over !== '—' && match.total_over !== '0.00');
}

function hasDoubleChanceMarket(match) {
    return Boolean(match.p1x && match.p12 && match.px2);
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

function buildMatchMarketStrip(match, options) {
    const { isLive, externalUrl, totalMarket, doubleChance, teams, dateTimeText } = options;
    const parts = [];

    if (isLive) {
        parts.push('<span class="live-badge"><span class="live-dot"></span>LIVE</span>');
    }

    if (totalMarket) {
        parts.push(`<button class="market-chip market-chip--total" type="button" onclick="if(navigator.vibrate)navigator.vibrate(20);window.openBetSlip('${match.id}','${teams.replace(/'/g, "\\'")}','ТБ ${match.total_value}','${escapeHtml(match.total_over)}','${dateTimeText}','${escapeHtml(match.league || '').replace(/'/g, "\\'")}')">Тотал ${escapeHtml(String(match.total_value))}</button>`);
    }

    if (doubleChance) {
        parts.push('<span class="market-chip market-chip--secondary">1X • 12 • X2</span>');
    }

    if (externalUrl) {
        const safeUrl = escapeHtml(externalUrl);
        parts.push(`<a class="match-link match-link--external" href="${safeUrl}" target="_blank" rel="noopener noreferrer nofollow">${isLive ? 'Live-центр' : 'Открыть матч'}</a>`);
    }

    if (!parts.length) return '';
    return `<div class="match-market-strip">${parts.join('')}</div>`;
}

function buildResultCard(match, isFavorite) {
    const team1 = escapeHtml(match.team1 || match.home_team || '');
    const team2 = escapeHtml(match.team2 || match.away_team || '');
    const externalUrl = getExternalMatchUrl(match);
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
        ${externalUrl ? `<div class="result-actions"><a class="result-link" href="${escapeHtml(externalUrl)}" target="_blank" rel="noopener noreferrer nofollow">Открыть матч</a></div>` : ''}
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
    const isLive = Boolean(match.is_live) || isMatchLive(match);
    const countdown = isLive ? '' : getCountdownText(match);
    const imminent = isMatchImminent(match, 15);
    const dateText = match.date || (match.match_time ? new Date(match.match_time).toLocaleDateString('ru-RU', { timeZone: 'Europe/Moscow', day: 'numeric', month: 'short' }) : 'Сегодня');
    const timeText = match.time || (match.match_time ? new Date(match.match_time).toLocaleTimeString('ru-RU', { timeZone: 'Europe/Moscow', hour: '2-digit', minute: '2-digit' }) : '');
    const dateTimeText = escapeHtml(`${dateText} ${timeText}`.trim());
    const sport = getMatchSport(match);
    const countdownClasses = ['countdown'];
    if (imminent) countdownClasses.push('countdown--imminent');
    const externalUrl = getExternalMatchUrl(match);
    const totalMarket = hasTotalMarket(match);
    const doubleChance = sport === 'football' && hasDoubleChanceMarket(match);

    const card = document.createElement('div');
    card.id = `match-${matchId}`;
    card.className = `match-card${isFavorite ? ' favorited' : ''}${imminent ? ' match-card--imminent' : ''}${isLive ? ' match-card--live' : ''}`;
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
        ${buildMatchMarketStrip(match, { isLive, externalUrl, totalMarket, doubleChance, teams, dateTimeText })}
        <div class="match-teams">${team1} <span class="vs">—</span> ${team2}</div>
        <div class="odds-container${totalMarket ? ' odds-container--with-totals' : ''}">
            <div class="odds-section-title">Основные исходы</div>
            ${buildOddButton('П1', match.p1 || match.odds_home, match, teams, dateTimeText)}
            ${buildOddButton('X', match.x || match.odds_draw, match, teams, dateTimeText)}
            ${buildOddButton('П2', match.p2 || match.odds_away, match, teams, dateTimeText)}
            ${doubleChance ? `<div class="odds-section-title">Двойной шанс</div>${buildOddButton('1X', match.p1x, match, teams, dateTimeText)}${buildOddButton('12', match.p12, match, teams, dateTimeText)}${buildOddButton('X2', match.px2, match, teams, dateTimeText)}` : ''}
            ${totalMarket ? `<div class="odds-section-title odds-section-title--accent">Тотал (${match.total_value})</div>${buildOddButton(`ТБ ${match.total_value}`, match.total_over, match, teams, dateTimeText)}${buildOddButton(`ТМ ${match.total_value}`, match.total_under, match, teams, dateTimeText)}<div></div>` : ''}
        </div>
    `;

    return card;
}

export function patchCardOdds(card, match, favorites) {
    const isFavorite = favorites.includes(match.id);
    const imminent = isMatchImminent(match, 15);
    const isLive = Boolean(match.is_live) || isMatchLive(match);

    card.classList.toggle('favorited', isFavorite);
    card.classList.toggle('match-card--imminent', imminent);
    card.classList.toggle('match-card--live', isLive);

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

function formatSnapshotStamp(raw) {
    if (!raw) return '';
    const parsed = new Date(raw);
    if (Number.isNaN(parsed.getTime())) return escapeHtml(String(raw));
    return parsed.toLocaleString('ru-RU', {
        timeZone: 'Europe/Moscow',
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function buildStaleSnapshotNotice(meta, matches) {
    const snapshotTime = formatSnapshotStamp(meta?.last_update);
    const visibleCount = Array.isArray(matches) ? matches.length : 0;
    const countLabel = visibleCount ? `Сейчас показан последний доступный снимок линии: ${visibleCount} событий.` : 'Сейчас показан последний доступный снимок линии.';
    const timeLabel = snapshotTime ? `Последнее обновление: ${snapshotTime}.` : 'Время последнего обновления сохранено в кэше.';
    return `
        <section class="section section--notice">
            <div class="stale-snapshot-notice">
                <div class="stale-snapshot-notice__eyebrow">Архивный снимок линии</div>
                <div class="stale-snapshot-notice__title">Свежий фид недоступен, поэтому сайт показывает последний сохранённый срез.</div>
                <div class="stale-snapshot-notice__text">${countLabel} ${timeLabel}</div>
            </div>
        </section>
    `;
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

export function renderMatches(matches, options = {}) {
    const container = document.getElementById('content');
    if (!container) return;

    if (observer) {
        observer.disconnect();
        observer = null;
    }

    const meta = options.meta || {};

    if (!matches.length) {
        if (meta.isStale && Array.isArray(options.sourceMatches) && options.sourceMatches.length && !options.staleFallback) {
            container.innerHTML = `${buildStaleSnapshotNotice(meta, options.sourceMatches)}<div class="section"><p style="text-align:center; color:var(--text-tertiary);">Свежих матчей в текущем окне нет. Обновите линию позже или откройте полный фид.</p></div>`;
            return;
        }
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

    container.innerHTML = options.staleFallback ? buildStaleSnapshotNotice(meta, matches) : '';

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
