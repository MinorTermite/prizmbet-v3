/**
 * PrizmBet v2 - UI Module
 */
import { escapeHtml, getCountdownText, parseMatchDateTime, isMatchLive } from './utils.js';
import { getFavorites } from './storage.js';
import { getMatchGame, getMatchSport } from './filters.js';

export function updateStats(matches) {
    const totalMatches = document.getElementById('totalMatches');
    const totalLeagues = document.getElementById('totalLeagues');
    const avgOdds = document.getElementById('avgOdds');
    
    if (totalMatches) totalMatches.textContent = matches.length;
    if (totalLeagues) totalLeagues.textContent = new Set(matches.map(m => m.league)).size;
    
    if (avgOdds) {
        const avg = matches.reduce((s, m) => s + ((parseFloat(m.p1) || 0) + (parseFloat(m.p2) || 0)) / 2, 0) / Math.max(matches.length, 1);
        avgOdds.textContent = avg.toFixed(2);
    }
}

export function buildGameFilter(matches) {
    const sel = document.getElementById('gameFilter');
    if (!sel) return;
    const set = new Set();
    matches.forEach(m => set.add(getMatchGame(m)));
    const games = Array.from(set).sort((a, b) => a.localeCompare(b, 'ru'));
    const prev = sel.value || 'all';
    sel.innerHTML = '<option value="all">Все лиги</option>' +
        games.map(g => `<option value="${escapeHtml(g)}">${escapeHtml(g)}</option>`).join('');
    // 'all' is hardcoded first option — not in games array, restore it explicitly
    sel.value = (prev === 'all' || games.includes(prev)) ? prev : 'all';
}

export function createMatchCard(match, favorites) {
    const eid = match.id || '';
    const isFav = favorites.includes(match.id);
    const t1 = escapeHtml(match.team1 || match.home_team || '');
    const t2 = escapeHtml(match.team2 || match.away_team || '');
    const teams = `${t1} vs ${t2}`;
    const countdown = getCountdownText(match);
    const shortId = String(eid).replace(/^[a-z]+_/i, '').slice(-6);
    
    // Если матч завершен
    if (match.score) {
        let score1 = '-', score2 = '-';
        if (match.score.includes(':')) {
            const parts = match.score.split(':');
            score1 = parts[0].trim();
            score2 = parts[1].trim();
        } else if (match.score.includes('-')) {
            const parts = match.score.split('-');
            score1 = parts[0].trim();
            score2 = parts[1].trim();
        } else {
            score1 = match.score;
            score2 = '';
        }

        const init1 = t1.substring(0, 2).toUpperCase();
        const init2 = t2.substring(0, 2).toUpperCase();
        
        const card = document.createElement('div');
        card.id = `match-${eid}`;
        card.className = 'match-result-card' + (isFav ? ' favorited' : '');
        
        const dateStr = match.date || (match.match_time ? new Date(match.match_time).toLocaleDateString('ru-RU', {timeZone: 'Europe/Moscow'}) : '');
        const timeStr = match.time || (match.match_time ? new Date(match.match_time).toLocaleTimeString('ru-RU', {timeZone: 'Europe/Moscow', hour: '2-digit', minute:'2-digit'}) : '');
        const headerText = `${escapeHtml(match.league || '')}, ${escapeHtml(dateStr)} ${escapeHtml(timeStr)}`;
        
        card.innerHTML = `
            <div class="result-header">${headerText}</div>
            <div class="result-body">
                <div class="team-block home">
                    <div class="team-name">${t1}</div>
                    <div class="team-logo">${init1}</div>
                </div>
                <div class="score-block">
                    <div class="score-row">
                        <div class="score-box">${escapeHtml(score1)}</div>
                        <div class="score-box">${escapeHtml(score2)}</div>
                    </div>
                    <div class="match-status-text">Завершен</div>
                </div>
                <div class="team-block away">
                    <div class="team-logo">${init2}</div>
                    <div class="team-name">${t2}</div>
                </div>
            </div>
        `;
        return card;
    }

    // Активный матч
    const dateStr = match.date || (match.match_time ? new Date(match.match_time).toLocaleDateString('ru-RU', {timeZone: 'Europe/Moscow', day: 'numeric', month: 'short'}) : 'Сегодня');
    const timeStr = match.time || (match.match_time ? new Date(match.match_time).toLocaleTimeString('ru-RU', {timeZone: 'Europe/Moscow', hour: '2-digit', minute:'2-digit'}) : '');
    const dt = escapeHtml(`${dateStr} ${timeStr}`);
    
    function oddBtn(label, value) {
        const raw = value || '';
        const unavail = !raw || raw === '—' || raw === '-' || raw === '0.00' || parseFloat(raw) < 1.01;
        const val = escapeHtml(unavail ? '—' : raw);
        const lg = escapeHtml(match.league || '');
        const lgJs = lg.replace(/'/g, "\\'");
        if (unavail) return `<div class="odd-item odd-item--na" data-bet="${label}"><div class="odd-label">${label}</div><div class="odd-value">${val}</div></div>`;
        return `<div class="odd-item" data-bet="${label}" onclick="if(navigator.vibrate)navigator.vibrate(20);window.openBetSlip('${eid}','${teams.replace(/'/g,"\\'")}','${label}','${val}','${dt}','${lgJs}')"><div class="odd-label">${label}</div><div class="odd-value">${val}</div></div>`;
    }
    
    const card = document.createElement('div');
    card.id = `match-${eid}`;
    card.className = 'match-card' + (isFav ? ' favorited' : '');
    
    const sport = getMatchSport(match);
    
    card.innerHTML = `
        <div class="match-header">
            <a class="match-id" href="#match-${eid}" onclick="window.shareMatch('${eid}');return false;" title="ID: ${eid}">#${shortId}</a>
            <div class="match-actions">
                <button class="share-btn" onclick="window.shareMatch('${eid}')" title="Поделиться матчем">🔗</button>
                <button class="favorite-btn ${isFav?'active':''}" onclick="window.toggleFavorite('${eid}')" title="${isFav?'Убрать из избранного':'В избранное'}">★</button>
            </div>
        </div>
        <div class="match-time">${dt}${countdown?`<span class="countdown${countdown==='LIVE'?' live-badge':''}">${countdown}</span>`:''}</div>
        <div class="match-teams">${t1} <span class="vs">—</span> ${t2}</div>
        <div class="odds-container">
            <div class="odds-section-title">Основные</div>
            ${oddBtn('П1', match.p1 || match.odds_home)}
            ${oddBtn('X', match.x || match.odds_draw)}
            ${oddBtn('П2', match.p2 || match.odds_away)}
            
            ${sport === 'football' ? `<div class="odds-section-title">Двойной шанс</div>${oddBtn('1X',match.p1x)}${oddBtn('12',match.p12)}${oddBtn('X2',match.px2)}` : ''}
            
            ${(match.total_over && match.total_over!=='0.00' && match.total_value) ? `<div class="odds-section-title">Тотал (${match.total_value})</div>${oddBtn('ТБ '+match.total_value, match.total_over)}${oddBtn('ТМ '+match.total_value, match.total_under)}<div></div>` : ''}
        </div>`;
    return card;
}

export function patchCardOdds(card, match, favorites) {
    const eid = match.id || '';
    const isFav = favorites.includes(match.id);
    
    if (isFav) card.classList.add('favorited'); else card.classList.remove('favorited');
    const favBtn = card.querySelector('.favorite-btn');
    if (favBtn) { 
        favBtn.classList.toggle('active', isFav); 
        favBtn.title = isFav ? 'Убрать из избранного' : 'В избранное'; 
    }
    
    const oddMap = { 
        'П1': match.p1 || match.odds_home, 
        'X': match.x || match.odds_draw, 
        'П2': match.p2 || match.odds_away, 
        '1X': match.p1x, '12': match.p12, 'X2': match.px2,
        ['ТБ '+match.total_value]: match.total_over,
        ['ТМ '+match.total_value]: match.total_under
    };
    
    card.querySelectorAll('[data-bet]').forEach(btn => {
        const betType = btn.getAttribute('data-bet');
        const newRaw = oddMap[betType] || '';
        const unavail = !newRaw || newRaw === '—' || newRaw === '-' || newRaw === '0.00' || parseFloat(newRaw) < 1.01;
        const newVal = unavail ? '—' : newRaw;
        const valEl = btn.querySelector('.odd-value');
        if (!valEl) return;
        
        if (valEl.textContent !== newVal) {
            valEl.textContent = newVal;
            valEl.classList.remove('odd-changed');
            void valEl.offsetWidth; // reflow
            valEl.classList.add('odd-changed');
            setTimeout(() => valEl.classList.remove('odd-changed'), 900);
        }
        
        if (!unavail) {
            const t1 = escapeHtml(match.team1 || match.home_team || '');
            const t2 = escapeHtml(match.team2 || match.away_team || '');
            const teams = `${t1} vs ${t2}`;
            const dateStr = match.date || (match.match_time ? new Date(match.match_time).toLocaleDateString('ru-RU') : 'Сегодня');
            const timeStr = match.time || (match.match_time ? new Date(match.match_time).toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'}) : '');
            const dt = escapeHtml(`${dateStr} ${timeStr}`);
            const lg = escapeHtml(match.league || '');
            
            btn.onclick = () => window.openBetSlip(eid, teams, betType, newVal, dt, lg);
            btn.className = 'odd-item';
        } else {
            btn.onclick = null;
            btn.className = 'odd-item odd-item--na';
        }
    });
}

// ── Pagination state ──────────────────────────────────────────────────────────
const LEAGUES_PER_PAGE = 6;   // leagues rendered per IntersectionObserver tick
let _ioObserver = null;        // active IntersectionObserver

function _renderLeagueChunk(container, pendingLeagues, matchesMap, favs) {
    const chunk = pendingLeagues.splice(0, LEAGUES_PER_PAGE);
    chunk.forEach(league => {
        const section = document.createElement('div');
        section.className = 'section';
        section.innerHTML = `<h2 class="section-title">${escapeHtml(league)}</h2>`;
        (matchesMap[league] || []).forEach(m => section.appendChild(createMatchCard(m, favs)));
        container.appendChild(section);
    });

    if (pendingLeagues.length > 0) {
        _attachSentinel(container, pendingLeagues, matchesMap);
    }
}

function _attachSentinel(container, pendingLeagues, matchesMap) {
    if (_ioObserver) { _ioObserver.disconnect(); _ioObserver = null; }

    const sentinel = document.createElement('div');
    sentinel.id = 'load-more-sentinel';
    sentinel.style.cssText = 'height:1px;width:100%;pointer-events:none;';
    container.appendChild(sentinel);

    _ioObserver = new IntersectionObserver(entries => {
        if (!entries[0].isIntersecting) return;
        _ioObserver.disconnect();
        _ioObserver = null;
        sentinel.remove();
        _renderLeagueChunk(container, pendingLeagues, matchesMap, getFavorites());
    }, { rootMargin: '400px' });

    _ioObserver.observe(sentinel);
}

export function renderMatches(matches) {
    const container = document.getElementById('content');
    if (!container) return;

    // Disconnect any pending observer from the previous render
    if (_ioObserver) { _ioObserver.disconnect(); _ioObserver = null; }

    if (matches.length === 0) {
        container.innerHTML = '<div class="section"><p style="text-align:center; color:var(--text-tertiary);">Матчи не найдены</p></div>';
        return;
    }

    const favs = getFavorites();

    // Group by league (preserve order; filterMatches already excludes scored matches from main list)
    const matchesMap = {};
    const leagueOrder = [];
    matches.forEach(m => {
        if (!matchesMap[m.league]) { matchesMap[m.league] = []; leagueOrder.push(m.league); }
        matchesMap[m.league].push(m);
    });

    container.innerHTML = '';

    // If navigating via shared hash link — render ALL leagues immediately so the element exists
    const hash = window.location.hash;
    const anchorId = (hash && hash.startsWith('#match-')) ? hash.slice(1) : null;

    if (anchorId) {
        // Skip lazy-loading: render every league now so anchor element is in DOM
        leagueOrder.forEach(league => {
            const section = document.createElement('div');
            section.className = 'section';
            section.innerHTML = `<h2 class="section-title">${escapeHtml(league)}</h2>`;
            (matchesMap[league] || []).forEach(m => section.appendChild(createMatchCard(m, favs)));
            container.appendChild(section);
        });
        requestAnimationFrame(() => {
            const el = document.getElementById(anchorId);
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    } else {
        _renderLeagueChunk(container, leagueOrder, matchesMap, favs);
    }
}
