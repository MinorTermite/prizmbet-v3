const MASTER_WALLET = 'PRIZM-4N7T-L2A7-RQZA-5BETW';
const STORAGE_KEY = 'prizmbet_intent_lab_v1';
const STATUS_LABELS = {
    awaiting_payment: 'Ожидает перевода',
    accepted: 'Accepted',
    rejected: 'Rejected',
    expired: 'Истёк',
    won: 'Win',
    lost: 'Loss',
};
const REJECT_LABELS = {
    LATE_BET: 'Ставка пришла после безопасного окна',
    SENDER_MISMATCH: 'Перевод пришёл с другого кошелька',
    INVALID_INTENT: 'Код не распознан',
    INTENT_EXPIRED: 'Intent уже истёк',
};
const OUTCOMES = [
    { label: 'П1', apiOutcome: 'P1', keys: ['p1', 'odds_home'] },
    { label: 'X', apiOutcome: 'X', keys: ['x', 'odds_draw'] },
    { label: 'П2', apiOutcome: 'P2', keys: ['p2', 'odds_away'] },
];

const state = {
    wallet: '',
    amount: 1500,
    apiBase: '',
    apiLive: false,
    matches: [],
    activeIntent: null,
    history: [],
    dashboard: null,
};

const el = {};

document.addEventListener('DOMContentLoaded', async () => {
    bindElements();
    restoreState();
    bindEvents();
    syncInputs();
    await loadMatches();
    await checkApi(false);
    renderAll();
    setInterval(tickCountdown, 1000);
});

function bindElements() {
    Object.assign(el, {
        walletInput: document.getElementById('walletInput'),
        amountInput: document.getElementById('amountInput'),
        apiBaseInput: document.getElementById('apiBaseInput'),
        checkApiBtn: document.getElementById('checkApiBtn'),
        apiHint: document.getElementById('apiHint'),
        apiModeBadge: document.getElementById('apiModeBadge'),
        matchesGrid: document.getElementById('matchesGrid'),
        intentEmpty: document.getElementById('intentEmpty'),
        intentCard: document.getElementById('intentCard'),
        selectedSource: document.getElementById('selectedSource'),
        intentStatusPill: document.getElementById('intentStatusPill'),
        intentCountdown: document.getElementById('intentCountdown'),
        intentMatch: document.getElementById('intentMatch'),
        intentOutcome: document.getElementById('intentOutcome'),
        intentOdds: document.getElementById('intentOdds'),
        intentAmount: document.getElementById('intentAmount'),
        intentMode: document.getElementById('intentMode'),
        intentHash: document.getElementById('intentHash'),
        transferInstructions: document.getElementById('transferInstructions'),
        intentTimeline: document.getElementById('intentTimeline'),
        copyCodeBtn: document.getElementById('copyCodeBtn'),
        refreshStatusBtn: document.getElementById('refreshStatusBtn'),
        simulateAcceptBtn: document.getElementById('simulateAcceptBtn'),
        simulateLateBtn: document.getElementById('simulateLateBtn'),
        simulateMismatchBtn: document.getElementById('simulateMismatchBtn'),
        simulateWonBtn: document.getElementById('simulateWonBtn'),
        simulateLostBtn: document.getElementById('simulateLostBtn'),
        cabinetModeBadge: document.getElementById('cabinetModeBadge'),
        cabinetWallet: document.getElementById('cabinetWallet'),
        rankName: document.getElementById('rankName'),
        rankHint: document.getElementById('rankHint'),
        rankProgressText: document.getElementById('rankProgressText'),
        rankProgressBar: document.getElementById('rankProgressBar'),
        statsGrid: document.getElementById('statsGrid'),
        cabinetFeed: document.getElementById('cabinetFeed'),
        toast: document.getElementById('toast'),
    });
}

function bindEvents() {
    el.walletInput.addEventListener('input', () => {
        state.wallet = el.walletInput.value.trim().toUpperCase();
        persistState();
        renderCabinet();
        if (state.wallet) loadDashboard();
    });

    el.amountInput.addEventListener('input', () => {
        state.amount = Math.max(Number(el.amountInput.value) || 0, 0);
        persistState();
        renderIntentCard();
    });

    el.apiBaseInput.addEventListener('input', () => {
        state.apiBase = normalizeApiBase(el.apiBaseInput.value);
        persistState();
    });

    el.checkApiBtn.addEventListener('click', () => checkApi(true));
    el.copyCodeBtn.addEventListener('click', copyIntentCode);
    el.refreshStatusBtn.addEventListener('click', refreshIntentStatus);
    el.simulateAcceptBtn.addEventListener('click', () => simulateIntent('accepted'));
    el.simulateLateBtn.addEventListener('click', () => simulateIntent('rejected', 'LATE_BET'));
    el.simulateMismatchBtn.addEventListener('click', () => simulateIntent('rejected', 'SENDER_MISMATCH'));
    el.simulateWonBtn.addEventListener('click', () => simulateIntent('won'));
    el.simulateLostBtn.addEventListener('click', () => simulateIntent('lost'));
}

function restoreState() {
    try {
        const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        state.wallet = parsed.wallet || '';
        state.amount = Number(parsed.amount || 1500);
        state.apiBase = parsed.apiBase || '';
        state.activeIntent = parsed.activeIntent || null;
        state.history = Array.isArray(parsed.history) ? parsed.history : [];
    } catch (_) {
        state.history = [];
    }
}

function persistState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
        wallet: state.wallet,
        amount: state.amount,
        apiBase: state.apiBase,
        activeIntent: state.activeIntent,
        history: state.history,
    }));
}

function restorePrefillFromQuery() {
    const params = new URLSearchParams(window.location.search);
    const rawOutcome = params.get('outcome') || '';
    const rawApiOutcome = params.get('api_outcome') || mapOutcomeToApiOutcome(rawOutcome);
    const teams = params.get('teams') || '';
    const matchId = params.get('match_id') || '';
    const coef = params.get('coef') || '';
    const amount = Number(params.get('amount') || 0);
    const league = params.get('league') || 'Переход из основного купона';
    const matchTime = params.get('datetime') || '';
    const parts = splitTeams(teams);
    const outcome = OUTCOMES.find((item) => item.apiOutcome === rawApiOutcome) || {
        label: rawOutcome || rawApiOutcome || 'P1',
        apiOutcome: rawApiOutcome || 'P1',
        keys: [],
    };

    if (!matchId && !teams && !rawOutcome) return;
    if (amount > 0) state.amount = amount;

    state.activeIntent = null;
    state.prefillSelection = {
        match: {
            id: matchId || 'prefill',
            team1: parts[0] || teams,
            team2: parts[1] || '',
            league,
            match_time: matchTime,
        },
        teams,
        odd: coef,
        outcome,
    };
}

function splitTeams(teams) {
    const raw = String(teams || '').trim();
    if (!raw) return ['', ''];
    const patterns = [' — ', ' - ', ' vs ', ' VS ', ' v '];
    for (const pattern of patterns) {
        if (raw.includes(pattern)) {
            const parts = raw.split(pattern).map((item) => item.trim());
            return [parts[0] || '', parts.slice(1).join(pattern).trim() || ''];
        }
    }
    return [raw, ''];
}

function mapOutcomeToApiOutcome(label) {
    const normalized = String(label || '').trim().toUpperCase();
    if (normalized === 'П1') return 'P1';
    if (normalized === 'П2') return 'P2';
    if (normalized === 'X') return 'X';
    return normalized;
}

function syncInputs() {
    el.walletInput.value = state.wallet;
    el.amountInput.value = String(state.amount || 1500);
    el.apiBaseInput.value = state.apiBase;
}

async function loadMatches() {
    try {
        const response = await fetch(`matches-today.json?v=${Date.now()}`);
        const payload = await response.json();
        state.matches = (payload.matches || []).filter((match) => !match.score).slice(0, 9);
    } catch (_) {
        el.matchesGrid.innerHTML = '<div class="empty-box">Не удалось загрузить matches-today.json. Прототип всё равно можно смотреть, но без витрины матчей.</div>';
        showToast('Не удалось загрузить линию для прототипа.');
    }
}

async function checkApi(showFeedback = true) {
    const base = normalizeApiBase(state.apiBase);
    if (!base) {
        state.apiLive = false;
        state.dashboard = null;
        renderApiMode('demo', 'API base URL не задан, страница работает в demo mode.');
        return;
    }

    try {
        const response = await fetch(`${base}/health`, { mode: 'cors' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        state.apiLive = true;
        renderApiMode('live', `API найден по адресу ${base}. Можно создавать real intent и опрашивать статусы.`);
        if (state.wallet) await loadDashboard();
        if (showFeedback) showToast('API доступен. Прототип переключен в live mode.');
    } catch (_) {
        state.apiLive = false;
        state.dashboard = null;
        renderApiMode('demo', 'API не ответил. Включён интерактивный demo flow для UX-проверки.');
        if (showFeedback) showToast('API недоступен, работаем в demo mode.');
    }
}

function renderApiMode(mode, message) {
    el.apiModeBadge.textContent = mode === 'live' ? 'LIVE API' : 'DEMO MODE';
    el.apiModeBadge.className = `status-pill ${mode === 'live' ? 'status-pill--accepted' : 'status-pill--demo'}`;
    el.apiHint.textContent = message;
    el.cabinetModeBadge.textContent = mode === 'live' ? 'Данные API + локальный preview' : 'Локальный preview';
}

function renderAll() {
    renderMatches();
    renderIntentCard();
    renderCabinet();
}

function renderMatches() {
    if (!state.matches.length) return;
    el.matchesGrid.innerHTML = '';
    state.matches.forEach((match) => {
        const card = document.createElement('article');
        card.className = 'match-card';
        const matchTime = formatDateTime(match.match_time || `${match.date || ''} ${match.time || ''}`);
        card.innerHTML = `
            <div class="match-topline">
                <span>${escapeHtml(match.league || 'Без лиги')}</span>
                <span>${escapeHtml(matchTime)}</span>
            </div>
            <div class="match-title">${escapeHtml(match.team1 || '')} — ${escapeHtml(match.team2 || '')}</div>
            <div class="market-row"></div>
        `;
        const marketRow = card.querySelector('.market-row');
        OUTCOMES.forEach((outcome) => {
            const odd = getMatchOdd(match, outcome.keys);
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'market-btn';
            if (!odd) {
                button.classList.add('market-btn--na');
                button.disabled = true;
            }
            button.innerHTML = `<span>${outcome.label}</span><strong>${odd || '—'}</strong>`;
            button.addEventListener('click', () => handleOutcomeSelect(match, outcome, odd));
            marketRow.appendChild(button);
        });
        el.matchesGrid.appendChild(card);
    });
}

function getMatchOdd(match, keys) {
    for (const key of keys) {
        const raw = match[key];
        if (!raw || raw === '-' || raw === '—' || raw === '0.00') continue;
        return String(raw);
    }
    return '';
}

async function handleOutcomeSelect(match, outcome, odd) {
    if (!state.wallet) {
        el.walletInput.focus();
        showToast('Сначала введите кошелёк игрока.');
        return;
    }
    if (!state.amount || state.amount < 10) {
        el.amountInput.focus();
        showToast('Укажите тестовую сумму ставки.');
        return;
    }

    const intent = await createIntentRecord(match, outcome, odd);
    state.activeIntent = intent;
    upsertHistory(intent);
    persistState();
    renderAll();
    await loadDashboard();
}

async function createIntentRecord(match, outcome, odd) {
    const base = normalizeApiBase(state.apiBase);
    const amount = Number(state.amount || 0);
    const common = {
        intent_hash: generateIntentHash(),
        sender_wallet: state.wallet,
        amount_prizm: amount,
        odds_fixed: Number(odd || 0),
        outcome: outcome.label,
        api_outcome: outcome.apiOutcome,
        match_id: String(match.id || ''),
        match_label: `${match.team1 || ''} — ${match.team2 || ''}`,
        league: match.league || '',
        match_time: match.match_time || '',
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        status: 'awaiting_payment',
        mode: 'demo',
        reject_reason: '',
        timeline: [{
            title: 'Intent выпущен',
            description: 'Сайт зафиксировал исход и подготовил одноразовый код для перевода.',
            at: new Date().toISOString(),
        }],
    };

    if (state.apiLive && base) {
        try {
            const response = await fetch(`${base}/api/intents`, {
                method: 'POST',
                mode: 'cors',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    match_id: common.match_id,
                    outcome: outcome.apiOutcome,
                    sender_wallet: state.wallet,
                }),
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const payload = await response.json();
            common.intent_hash = payload.intent_hash || common.intent_hash;
            common.odds_fixed = Number(payload.odds_fixed || common.odds_fixed);
            common.expires_at = payload.expires_at || common.expires_at;
            common.mode = 'live';
            common.timeline.push({
                title: 'Intent записан в backend',
                description: 'Код сохранён в bet_intents и готов к проверке listener-ом.',
                at: new Date().toISOString(),
            });
            showToast('Создан реальный intent через API.');
        } catch (_) {
            common.timeline.push({
                title: 'Fallback в demo mode',
                description: 'API не ответил на create_intent, поэтому оставили локальный preview.',
                at: new Date().toISOString(),
            });
            showToast('Create intent не ответил, использован demo flow.');
        }
    }

    return common;
}

function upsertHistory(record) {
    const index = state.history.findIndex((item) => item.intent_hash === record.intent_hash);
    if (index >= 0) state.history[index] = record;
    else state.history.unshift(record);
    state.history = state.history.slice(0, 24);
}

function renderIntentCard() {
    const intent = state.activeIntent;
    if (!intent) {
        el.intentEmpty.classList.remove('hidden');
        el.intentCard.classList.add('hidden');

        if (state.prefillSelection) {
            const matchLabel = state.prefillSelection.teams || [state.prefillSelection.match.team1, state.prefillSelection.match.team2].filter(Boolean).join(' — ');
            el.selectedSource.textContent = 'Переход из основного купона';
            el.intentEmpty.innerHTML = `
                <div class="prefill-box">
                    <div class="summary-label">Исход уже выбран на основном сайте</div>
                    <div class="prefill-title">${escapeHtml(matchLabel)}</div>
                    <div class="prefill-caption">${escapeHtml(state.prefillSelection.outcome.label)} @ ${escapeHtml(state.prefillSelection.odd || '—')} • ${escapeHtml(state.prefillSelection.match.league || 'Без лиги')}</div>
                    <div class="prefill-caption">Теперь старый комментарий больше не нужен: сайт выпустит короткий intent-код и покажет следующий шаг для перевода.</div>
                    <button id="launchPrefillIntentBtn" class="primary-btn" type="button">Выпустить intent по этому купону</button>
                </div>
            `;
            document.getElementById('launchPrefillIntentBtn')?.addEventListener('click', launchPrefillIntent);
            return;
        }

        el.selectedSource.textContent = 'Ожидает выбора';
        el.intentEmpty.innerHTML = 'Выберите исход слева. После этого прототип выпустит одноразовый код ставки, зафиксирует коэффициент и покажет, что именно игрок должен отправить в сеть.';
        return;
    }

    autoExpireIntent(intent);
    const statusMeta = getStatusMeta(intent.status);

    el.intentEmpty.classList.add('hidden');
    el.intentCard.classList.remove('hidden');
    el.selectedSource.textContent = intent.mode === 'live' ? 'Intent создан через API' : 'Локальный demo intent';
    el.intentStatusPill.textContent = STATUS_LABELS[intent.status] || intent.status;
    el.intentStatusPill.className = `status-pill ${statusMeta.className}`;
    el.intentCountdown.textContent = formatCountdown(intent.expires_at);
    el.intentMatch.textContent = intent.match_label;
    el.intentOutcome.textContent = intent.outcome;
    el.intentOdds.textContent = formatNumber(intent.odds_fixed);
    el.intentAmount.textContent = `${formatNumber(intent.amount_prizm)} PRIZM`;
    el.intentMode.textContent = intent.mode === 'live' ? 'live intent' : 'demo preview';
    el.intentHash.textContent = intent.intent_hash;
    el.transferInstructions.textContent = `Отправьте ${formatNumber(intent.amount_prizm)} PRIZM на ${MASTER_WALLET} и вставьте в сообщение код ${intent.intent_hash}. Listener затем свяжет перевод с этим intent.`;

    renderTimeline(intent.timeline || []);
    const settled = intent.status === 'won' || intent.status === 'lost';
    const accepted = intent.status === 'accepted';
    el.simulateWonBtn.classList.toggle('hidden', !accepted);
    el.simulateLostBtn.classList.toggle('hidden', !accepted);
    el.simulateAcceptBtn.classList.toggle('hidden', accepted || settled || intent.status === 'rejected' || intent.status === 'expired');
    el.simulateLateBtn.classList.toggle('hidden', accepted || settled);
    el.simulateMismatchBtn.classList.toggle('hidden', accepted || settled);
}

function renderTimeline(items) {
    if (!items.length) {
        el.intentTimeline.innerHTML = '<div class="empty-box">Статусы пока не накопились.</div>';
        return;
    }
    el.intentTimeline.innerHTML = items.map((item) => `
        <div class="timeline-item">
            <strong>${escapeHtml(item.title)}</strong>
            <div>${escapeHtml(item.description)}</div>
            <small>${escapeHtml(formatDateTime(item.at))}</small>
        </div>
    `).join('');
}

async function refreshIntentStatus() {
    const intent = state.activeIntent;
    const base = normalizeApiBase(state.apiBase);
    if (!intent) return;
    if (!state.apiLive || !base) {
        showToast('Для live-обновления статуса нужен доступный API.');
        return;
    }

    try {
        const response = await fetch(`${base}/api/intents/${encodeURIComponent(intent.intent_hash)}`, { mode: 'cors' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const payload = await response.json();
        intent.status = payload.status || intent.status;
        if (payload.intent && payload.intent.expires_at) intent.expires_at = payload.intent.expires_at;
        if (payload.bet && payload.bet.reject_reason) intent.reject_reason = payload.bet.reject_reason;
        intent.timeline = [...(intent.timeline || []), {
            title: 'Статус синхронизирован',
            description: payload.bet ? `Listener вернул статус ${payload.status}.` : `Intent пока без связанной транзакции, статус ${payload.status}.`,
            at: new Date().toISOString(),
        }].slice(-8);
        state.activeIntent = { ...intent };
        upsertHistory(state.activeIntent);
        persistState();
        renderAll();
        await loadDashboard();
        showToast('Статус intent обновлён из API.');
    } catch (_) {
        showToast('Не удалось обновить статус из API.');
    }
}

function simulateIntent(nextStatus, rejectReason = '') {
    const intent = state.activeIntent;
    if (!intent) return;

    intent.status = nextStatus;
    intent.reject_reason = rejectReason;
    const descriptions = {
        accepted: 'Прототип показывает, что listener увидел перевод, сверил wallet и принял ставку.',
        rejected: REJECT_LABELS[rejectReason] || 'Listener отклонил ставку.',
        won: 'Прототип показывает следующий шаг после settlement: ставка выиграла и попадает в payout queue.',
        lost: 'Прототип показывает settlement без выплаты: ставка проиграла.',
    };
    intent.timeline = [...(intent.timeline || []), {
        title: `Симуляция: ${STATUS_LABELS[nextStatus] || nextStatus}`,
        description: descriptions[nextStatus] || 'Статус изменён локально.',
        at: new Date().toISOString(),
    }].slice(-8);
    state.activeIntent = { ...intent };
    upsertHistory(state.activeIntent);
    persistState();
    renderAll();
    renderCabinet();
    showToast(`Сценарий ${STATUS_LABELS[nextStatus] || nextStatus} применён.`);
}

async function loadDashboard() {
    if (!state.wallet) {
        state.dashboard = null;
        renderCabinet();
        return;
    }
    if (!state.apiLive || !state.apiBase) {
        state.dashboard = null;
        renderCabinet();
        return;
    }

    try {
        const response = await fetch(`${normalizeApiBase(state.apiBase)}/api/wallets/${encodeURIComponent(state.wallet)}/dashboard`, { mode: 'cors' });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        state.dashboard = await response.json();
    } catch (_) {
        state.dashboard = null;
    }
    renderCabinet();
}

function renderCabinet() {
    const wallet = state.wallet || 'Не выбран';
    el.cabinetWallet.textContent = wallet;

    const localRecords = state.history.filter((item) => item.sender_wallet === state.wallet);
    const stats = state.dashboard ? dashboardToStats(state.dashboard) : deriveLocalStats(localRecords);
    const feed = state.dashboard ? buildDashboardFeed(state.dashboard) : buildLocalFeed(localRecords);

    el.rankName.textContent = stats.rank.current;
    el.rankHint.textContent = stats.rank.next
        ? `До ${stats.rank.next.name} осталось ${formatNumber(stats.rank.next.remaining_prizm)} PRIZM turnover.`
        : 'Максимальный preview rank уже достигнут.';
    el.rankProgressText.textContent = `${stats.rank.progress_percent}%`;
    el.rankProgressBar.style.width = `${stats.rank.progress_percent}%`;

    el.statsGrid.innerHTML = `
        ${renderStat('Intent', stats.waiting_payment, 'ожидают перевода')}
        ${renderStat('Accepted', stats.accepted, 'приняты listener-ом')}
        ${renderStat('Rejected', stats.rejected, 'отклонены')}
        ${renderStat('Turnover', `${formatNumber(stats.turnover_prizm)} PZM`, 'учтённый объём')}
    `;

    if (!feed.length) {
        el.cabinetFeed.innerHTML = '<div class="empty-box">Выпустите первый intent, и здесь появится история по кошельку.</div>';
        return;
    }

    el.cabinetFeed.innerHTML = feed.map((item) => `
        <div class="feed-item">
            <strong>${escapeHtml(item.title)}</strong>
            <div>${escapeHtml(item.description)}</div>
            <small>${escapeHtml(item.meta)}</small>
        </div>
    `).join('');
}

function dashboardToStats(dashboard) {
    return {
        waiting_payment: dashboard.stats.waiting_payment || 0,
        accepted: dashboard.stats.accepted || 0,
        rejected: dashboard.stats.rejected || 0,
        turnover_prizm: dashboard.stats.turnover_prizm || 0,
        rank: dashboard.rank,
    };
}

function deriveLocalStats(records) {
    let waiting_payment = 0;
    let accepted = 0;
    let rejected = 0;
    let turnover_prizm = 0;

    records.forEach((record) => {
        if (record.status === 'awaiting_payment') waiting_payment += 1;
        if (['accepted', 'won', 'lost'].includes(record.status)) {
            accepted += 1;
            turnover_prizm += Number(record.amount_prizm || 0);
        }
        if (['rejected', 'expired'].includes(record.status)) rejected += 1;
    });

    return {
        waiting_payment,
        accepted,
        rejected,
        turnover_prizm,
        rank: deriveRank(turnover_prizm, accepted),
    };
}

function buildDashboardFeed(dashboard) {
    const items = [];
    (dashboard.recent_intents || []).forEach((intent) => {
        items.push({
            title: `${intent.intent_hash} • ${STATUS_LABELS[intent.status] || intent.status}`,
            description: `Исход ${intent.outcome} @ ${formatNumber(intent.odds_fixed)} • match ${intent.match_id}`,
            meta: formatDateTime(intent.created_at || intent.expires_at),
        });
    });
    return items.slice(0, 8);
}

function buildLocalFeed(records) {
    return records.slice(0, 8).map((record) => ({
        title: `${record.intent_hash} • ${STATUS_LABELS[record.status] || record.status}`,
        description: `${record.match_label} • ${record.outcome} @ ${formatNumber(record.odds_fixed)} • ${formatNumber(record.amount_prizm)} PRIZM${record.reject_reason ? ` • ${REJECT_LABELS[record.reject_reason] || record.reject_reason}` : ''}`,
        meta: formatDateTime(record.created_at),
    }));
}

function deriveRank(turnoverPrizm, acceptedCount) {
    const tiers = [
        { name: 'Observer', threshold: 0 },
        { name: 'Runner', threshold: 1500 },
        { name: 'Operator', threshold: 5000 },
        { name: 'Strategist', threshold: 15000 },
        { name: 'Imperator', threshold: 50000 },
    ];

    let current = tiers[0];
    let next = null;
    for (const tier of tiers) {
        if (turnoverPrizm >= tier.threshold) current = tier;
        else { next = tier; break; }
    }

    const span = next ? Math.max(next.threshold - current.threshold, 1) : 1;
    const progress = next ? Math.min(100, Math.round(((turnoverPrizm - current.threshold) / span) * 100)) : 100;

    return {
        current: current.name,
        accepted_count: acceptedCount,
        progress_percent: progress,
        next: next ? { name: next.name, remaining_prizm: Math.max(next.threshold - turnoverPrizm, 0) } : null,
    };
}

function renderStat(label, value, hint) {
    return `
        <div class="stat-card">
            <div class="summary-label">${label}</div>
            <div class="stat-value">${value}</div>
            <div class="rank-hint">${hint}</div>
        </div>
    `;
}

async function launchPrefillIntent() {
    if (!state.prefillSelection) return;
    if (!state.wallet) {
        el.walletInput.focus();
        showToast('Введите кошелек игрока, чтобы выпустить intent по выбранному купону.');
        return;
    }
    await handleOutcomeSelect(state.prefillSelection.match, state.prefillSelection.outcome, state.prefillSelection.odd);
}

function copyIntentCode() {
    if (!state.activeIntent || !state.activeIntent.intent_hash) return;
    navigator.clipboard.writeText(state.activeIntent.intent_hash).then(() => {
        showToast('Intent code скопирован.');
    }).catch(() => {
        showToast('Не удалось скопировать код.');
    });
}

function tickCountdown() {
    const intent = state.activeIntent;
    if (!intent) return;
    autoExpireIntent(intent);
    el.intentCountdown.textContent = formatCountdown(intent.expires_at);
    state.activeIntent = { ...intent };
    upsertHistory(state.activeIntent);
    persistState();
}

function autoExpireIntent(intent) {
    if (intent.status !== 'awaiting_payment') return intent;
    if (new Date(intent.expires_at).getTime() > Date.now()) return intent;
    intent.status = 'expired';
    intent.reject_reason = 'INTENT_EXPIRED';
    intent.timeline = [...(intent.timeline || []), {
        title: 'Intent истёк',
        description: 'В демо-контуре срок действия intent закончился до прихода перевода.',
        at: new Date().toISOString(),
    }].slice(-8);
    renderIntentCard();
    renderCabinet();
    return intent;
}

function getStatusMeta(status) {
    if (status === 'accepted') return { className: 'status-pill--accepted' };
    if (status === 'rejected') return { className: 'status-pill--rejected' };
    if (status === 'expired') return { className: 'status-pill--expired' };
    if (status === 'won' || status === 'lost') return { className: 'status-pill--settled' };
    return { className: 'status-pill--waiting' };
}

function normalizeApiBase(value) {
    return String(value || '').trim().replace(/\/$/, '');
}

function generateIntentHash() {
    return Math.random().toString(36).slice(2, 8).toUpperCase();
}

function formatNumber(value) {
    const num = Number(value || 0);
    return Number.isFinite(num) ? num.toLocaleString('ru-RU', { maximumFractionDigits: 2 }) : '0';
}

function formatCountdown(expiresAt) {
    const diff = new Date(expiresAt).getTime() - Date.now();
    if (diff <= 0) return '00:00';
    const totalSeconds = Math.floor(diff / 1000);
    const minutes = String(Math.floor(totalSeconds / 60)).padStart(2, '0');
    const seconds = String(totalSeconds % 60).padStart(2, '0');
    return `${minutes}:${seconds}`;
}

function formatDateTime(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value || '');
    return date.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(text) {
    return String(text || '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function showToast(message) {
    el.toast.textContent = message;
    el.toast.classList.remove('hidden');
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => el.toast.classList.add('hidden'), 2200);
}