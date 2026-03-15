const STORAGE_KEY = 'prizmbet_operator_console_v3';
const AUTO_REFRESH_MS = 20000;

const state = {
  apiBase: '',
  adminKey: '',
  query: '',
  status: '',
  autoRefresh: true,
  loading: false,
  items: [],
  auditItems: [],
  stats: null,
  meta: null,
  auditMeta: null,
  generatedAt: '',
  timer: null,
};

const dom = {};

function init() {
  cacheDom();
  bindEvents();
  restoreState();
  syncInputs();
  render();
  syncAutoRefresh();
  if (state.apiBase) fetchFeed();
}

function cacheDom() {
  dom.apiBaseInput = document.getElementById('apiBaseInput');
  dom.adminKeyInput = document.getElementById('adminKeyInput');
  dom.connectBtn = document.getElementById('connectBtn');
  dom.refreshBtn = document.getElementById('refreshBtn');
  dom.autoRefreshToggle = document.getElementById('autoRefreshToggle');
  dom.operatorStatus = document.getElementById('operatorStatus');
  dom.statsGrid = document.getElementById('statsGrid');
  dom.queryInput = document.getElementById('queryInput');
  dom.statusFilter = document.getElementById('statusFilter');
  dom.feedMeta = document.getElementById('feedMeta');
  dom.feedList = document.getElementById('feedList');
  dom.auditMeta = document.getElementById('auditMeta');
  dom.auditList = document.getElementById('auditList');
}

function bindEvents() {
  dom.connectBtn.addEventListener('click', () => {
    state.apiBase = normalizeApiBase(dom.apiBaseInput.value);
    state.adminKey = dom.adminKeyInput.value.trim();
    persistState();
    fetchFeed();
  });

  dom.refreshBtn.addEventListener('click', () => fetchFeed());

  dom.autoRefreshToggle.addEventListener('change', () => {
    state.autoRefresh = dom.autoRefreshToggle.checked;
    persistState();
    syncAutoRefresh();
    renderStatus(state.autoRefresh ? 'Auto refresh enabled.' : 'Auto refresh disabled.', 'neutral');
  });

  let debounceId = null;
  dom.queryInput.addEventListener('input', () => {
    state.query = dom.queryInput.value.trim();
    persistState();
    clearTimeout(debounceId);
    debounceId = setTimeout(fetchFeed, 280);
  });

  dom.statusFilter.addEventListener('change', () => {
    state.status = dom.statusFilter.value;
    persistState();
    fetchFeed();
  });

  dom.feedList.addEventListener('click', async (event) => {
    const copyButton = event.target.closest('[data-copy]');
    if (copyButton) {
      await copyValue(copyButton.getAttribute('data-copy') || '');
      return;
    }

    const paidButton = event.target.closest('[data-mark-paid]');
    if (paidButton) {
      await handleMarkPaid(paidButton);
    }
  });

  dom.auditList.addEventListener('click', async (event) => {
    const copyButton = event.target.closest('[data-copy]');
    if (!copyButton) return;
    await copyValue(copyButton.getAttribute('data-copy') || '');
  });
}

async function copyValue(value) {
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    renderStatus(`Copied: ${value}`, 'good');
  } catch {
    renderStatus('Failed to copy value to clipboard.', 'warn');
  }
}

function restoreState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    state.apiBase = normalizeApiBase(saved.apiBase || detectApiBase());
    state.adminKey = String(saved.adminKey || '');
    state.query = String(saved.query || '');
    state.status = String(saved.status || '');
    state.autoRefresh = saved.autoRefresh !== false;
  } catch {
    state.apiBase = detectApiBase();
  }
}

function persistState() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    apiBase: state.apiBase,
    adminKey: state.adminKey,
    query: state.query,
    status: state.status,
    autoRefresh: state.autoRefresh,
  }));
}

function syncInputs() {
  dom.apiBaseInput.value = state.apiBase;
  dom.adminKeyInput.value = state.adminKey;
  dom.queryInput.value = state.query;
  dom.statusFilter.value = state.status;
  dom.autoRefreshToggle.checked = state.autoRefresh;
}

function syncAutoRefresh() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
  if (state.autoRefresh) {
    state.timer = setInterval(() => {
      if (!state.loading) fetchFeed();
    }, AUTO_REFRESH_MS);
  }
}

function detectApiBase() {
  const host = window.location.hostname;
  if (host === '127.0.0.1' || host === 'localhost') {
    return 'http://127.0.0.1:8081';
  }
  return '';
}

function normalizeApiBase(value) {
  return String(value || '').trim().replace(/\/$/, '');
}

async function fetchFeed() {
  if (!state.apiBase) {
    state.items = [];
    state.auditItems = [];
    state.stats = null;
    state.meta = null;
    state.auditMeta = null;
    renderStatus('Set API base first. Use http://127.0.0.1:8081 for local operator mode.', 'warn');
    render();
    return;
  }

  if (window.location.protocol === 'https:' && state.apiBase.startsWith('http://127.0.0.1')) {
    renderStatus('An HTTPS page cannot read a local HTTP API. Open the operator page locally or use an HTTPS API.', 'bad');
    return;
  }

  state.loading = true;
  renderStatus('Loading operator data...', 'neutral');
  render();

  try {
    const feedUrl = new URL(`${state.apiBase}/api/admin/feed`);
    feedUrl.searchParams.set('limit', '80');
    if (state.query) feedUrl.searchParams.set('q', state.query);
    if (state.status) feedUrl.searchParams.set('status', state.status);

    const auditUrl = new URL(`${state.apiBase}/api/admin/audit-log`);
    auditUrl.searchParams.set('limit', '40');

    const headers = {};
    if (state.adminKey) headers['X-Admin-Key'] = state.adminKey;

    const [feedResponse, auditResponse] = await Promise.all([
      fetch(feedUrl.toString(), { headers }),
      fetch(auditUrl.toString(), { headers }),
    ]);

    const feedPayload = await feedResponse.json().catch(() => ({}));
    if (!feedResponse.ok) {
      throw new Error(feedPayload.error || `API returned ${feedResponse.status}`);
    }

    const auditPayload = await auditResponse.json().catch(() => ({}));
    if (!auditResponse.ok) {
      throw new Error(auditPayload.error || `Audit API returned ${auditResponse.status}`);
    }

    state.items = Array.isArray(feedPayload.items) ? feedPayload.items : [];
    state.auditItems = Array.isArray(auditPayload.items) ? auditPayload.items : [];
    state.stats = feedPayload.stats || null;
    state.meta = feedPayload.meta || null;
    state.auditMeta = auditPayload.meta || null;
    state.generatedAt = feedPayload.generated_at || auditPayload.generated_at || '';
    renderStatus(buildSuccessMessage(), 'good');
  } catch (error) {
    state.items = [];
    state.auditItems = [];
    state.stats = null;
    state.meta = null;
    state.auditMeta = null;
    renderStatus(error.message || 'Failed to load operator data.', 'bad');
  } finally {
    state.loading = false;
    render();
  }
}

function buildSuccessMessage() {
  if (state.meta && state.meta.db_configured === false) {
    return state.meta.message || 'Supabase is not configured yet. Feed is empty.';
  }
  const keyNote = state.meta?.admin_key_required ? 'Admin key required.' : 'Admin key not required.';
  const mirrorNote = state.auditMeta?.sheets_mirror_enabled ? 'Google Sheets mirror is ON.' : 'Google Sheets mirror is OFF.';
  return `Operator data loaded. ${keyNote} ${mirrorNote}`;
}

async function handleMarkPaid(button) {
  const txId = button.getAttribute('data-mark-paid') || '';
  const payoutAmount = Number(button.getAttribute('data-payout') || 0);
  if (!txId) return;
  if (!state.apiBase || !state.adminKey) {
    renderStatus('API base and admin key are required to mark payouts.', 'warn');
    return;
  }

  const payoutTxId = window.prompt('Enter payout TX ID. Leave empty if the transfer will be added later.', '') || '';
  button.disabled = true;
  try {
    const response = await fetch(`${state.apiBase}/api/admin/bets/${encodeURIComponent(txId)}/mark-paid`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': state.adminKey,
      },
      body: JSON.stringify({
        payout_tx_id: payoutTxId.trim(),
        payout_amount: payoutAmount || undefined,
      }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `API returned ${response.status}`);
    }
    renderStatus(`Bet ${txId} marked as paid.`, 'good');
    await fetchFeed();
  } catch (error) {
    renderStatus(error.message || 'Failed to mark payout.', 'bad');
  } finally {
    button.disabled = false;
  }
}

function renderStatus(message, tone) {
  dom.operatorStatus.textContent = String(message || 'No API connection.');
  dom.operatorStatus.dataset.tone = tone || 'neutral';
}

function render() {
  renderStats();
  renderFeedMeta();
  renderFeed();
  renderAuditMeta();
  renderAudit();
}

function renderStats() {
  const stats = state.stats;
  if (!stats) {
    dom.statsGrid.innerHTML = [
      buildStatCard('Feed size', '0'),
      buildStatCard('Accepted', '0'),
      buildStatCard('To payout', '0'),
      buildStatCard('Paid', '0'),
      buildStatCard('Turnover', '0 PRIZM'),
    ].join('');
    return;
  }

  dom.statsGrid.innerHTML = [
    buildStatCard('Feed size', formatNumber(stats.total_items)),
    buildStatCard('Accepted', formatNumber(stats.accepted_count)),
    buildStatCard('To payout', formatNumber(stats.to_payout_count ?? stats.won_count ?? 0)),
    buildStatCard('Paid', formatNumber(stats.paid_count ?? 0)),
    buildStatCard('Turnover', `${formatNumber(stats.turnover_prizm)} PRIZM`),
  ].join('');
}

function buildStatCard(label, value) {
  return `
    <article class="operator-stat-card">
      <div class="operator-stat-label">${escapeHtml(label)}</div>
      <div class="operator-stat-value">${escapeHtml(value)}</div>
    </article>
  `;
}

function renderFeedMeta() {
  const parts = [];
  if (state.loading) parts.push('Loading...');
  if (state.generatedAt) parts.push(`Updated ${formatDate(state.generatedAt)}`);
  if (state.items.length) parts.push(`${state.items.length} bets`);
  const payoutItems = state.items.filter((item) => item.status === 'won').length;
  if (payoutItems) parts.push(`To payout: ${payoutItems}`);
  dom.feedMeta.textContent = parts.join(' ? ') || 'Feed not loaded yet.';
}

function renderAuditMeta() {
  const parts = [];
  if (state.loading) parts.push('Loading...');
  if (state.auditItems.length) parts.push(`${state.auditItems.length} events`);
  parts.push(state.auditMeta?.sheets_mirror_enabled ? 'Google Sheets: ON' : 'Google Sheets: OFF');
  dom.auditMeta.textContent = parts.join(' ? ') || 'Audit log not loaded yet.';
}

function renderFeed() {
  if (!state.items.length) {
    dom.feedList.innerHTML = `
      <div class="operator-empty">
        <strong>No bets yet.</strong><br>
        When the listener or API records new items, they will appear here.
      </div>
    `;
    return;
  }

  dom.feedList.innerHTML = state.items.map(renderFeedCard).join('');
}

function renderAudit() {
  if (!state.auditItems.length) {
    dom.auditList.innerHTML = `
      <div class="operator-empty">
        <strong>No audit events yet.</strong><br>
        Backend and operator events will appear here as soon as they are written.
      </div>
    `;
    return;
  }

  dom.auditList.innerHTML = state.auditItems.map(renderAuditCard).join('');
}

function renderFeedCard(item) {
  const payoutAction = item.status === 'won'
    ? `<button class="operator-chip" type="button" data-mark-paid="${escapeAttr(item.tx_id || '')}" data-payout="${escapeAttr(item.potential_payout_prizm || 0)}">Mark paid</button>`
    : '';

  const rejectBlock = item.reject_reason
    ? `<div class="operator-reject">${escapeHtml(labelRejectReason(item.reject_reason))}</div>`
    : '';

  const payoutTxChip = item.payout_tx_id
    ? `<button class="operator-chip" type="button" data-copy="${escapeAttr(item.payout_tx_id)}">Payout TX</button>`
    : '';

  return `
    <article class="operator-card">
      <div class="operator-card-head">
        <div>
          <div class="operator-badges">
            <span class="operator-badge" data-tone="${escapeHtml(resolveStatusTone(item.status))}">${escapeHtml(labelStatus(item.status))}</span>
            <span class="operator-badge" data-tone="${escapeHtml(resolveMatchStateTone(item.match_state))}">${escapeHtml(labelMatchState(item.match_state))}</span>
          </div>
          <h3 class="operator-card-title">${escapeHtml(cleanText(item.match_label) || `Match #${item.match_id || '?'}`)}</h3>
          <p class="operator-card-copy">${escapeHtml(buildFeedSummary(item))}</p>
        </div>
        <div class="operator-actions">
          <button class="operator-chip" type="button" data-copy="${escapeAttr(item.intent_hash || '')}">Intent</button>
          <button class="operator-chip" type="button" data-copy="${escapeAttr(item.tx_id || '')}">TX</button>
          ${payoutTxChip}
          ${payoutAction}
        </div>
      </div>
      <div class="operator-card-grid">
        ${renderMeta('Intent', item.intent_hash || '?')}
        ${renderMeta('Wallet', item.sender_wallet || '?')}
        ${renderMeta('Outcome', `${labelOutcome(item.outcome)} @ ${item.odds_label || formatNumber(item.odds_fixed)}`)}
        ${renderMeta('Amount', `${formatNumber(item.amount_prizm)} PRIZM`)}
        ${renderMeta('Potential payout', `${formatNumber(item.potential_payout_prizm)} PRIZM`)}
        ${renderMeta('Time', formatDate(item.block_timestamp || item.created_at))}
      </div>
      ${rejectBlock}
    </article>
  `;
}

function renderAuditCard(item) {
  const payload = item.payload || {};
  const eventType = String(item.event_type || payload.event_type || '');
  const status = String(payload.status || item.status || '');
  const rejectReason = payload.reject_reason
    ? `<div class="operator-reject">${escapeHtml(labelRejectReason(payload.reject_reason))}</div>`
    : '';

  return `
    <article class="operator-card operator-card--audit">
      <div class="operator-card-head">
        <div>
          <div class="operator-badges">
            <span class="operator-badge" data-tone="${escapeHtml(resolveAuditTone(eventType, status))}">${escapeHtml(labelAuditEvent(eventType))}</span>
            <span class="operator-badge" data-tone="${escapeHtml(resolveStatusTone(status))}">${escapeHtml(labelStatus(status))}</span>
          </div>
          <h3 class="operator-card-title">${escapeHtml(cleanText(payload.match_label) || `Match #${payload.match_id || item.match_id || '?'}`)}</h3>
          <p class="operator-card-copy">${escapeHtml(buildAuditSummary(payload, item))}</p>
        </div>
        <div class="operator-actions">
          <button class="operator-chip" type="button" data-copy="${escapeAttr(payload.intent_hash || item.intent_hash || '')}">Intent</button>
          <button class="operator-chip" type="button" data-copy="${escapeAttr(payload.tx_id || item.tx_id || '')}">TX</button>
        </div>
      </div>
      <div class="operator-card-grid">
        ${renderMeta('Event type', labelAuditEvent(eventType))}
        ${renderMeta('Wallet', payload.sender_wallet || item.sender_wallet || '?')}
        ${renderMeta('Amount', `${formatNumber(payload.amount_prizm || item.amount_prizm)} PRIZM`)}
        ${renderMeta('Payout / potential', `${formatNumber(payload.payout_amount_prizm)} PRIZM`)}
        ${renderMeta('Match state', labelMatchState(payload.match_state || ''))}
        ${renderMeta('Time', formatDate(item.created_at || payload.created_at))}
      </div>
      ${rejectReason}
    </article>
  `;
}

function buildFeedSummary(item) {
  const match = cleanText(item.match_label) || `Match #${item.match_id || '?'}`;
  const outcome = labelOutcome(item.outcome);
  const odds = item.odds_label || formatNumber(item.odds_fixed);
  const amount = formatNumber(item.amount_prizm);
  return `${match} ? ${outcome} @ ${odds} ? ${amount} PRIZM`;
}

function buildAuditSummary(payload, item) {
  const match = cleanText(payload.match_label || item.match_label) || `Match #${payload.match_id || item.match_id || '?'}`;
  const outcome = labelOutcome(payload.outcome || item.outcome || '');
  const odds = payload.odds_fixed ? formatNumber(payload.odds_fixed) : (item.odds_label || formatNumber(item.odds_fixed));
  const amount = formatNumber(payload.amount_prizm || item.amount_prizm);
  return `${match} ? ${outcome} @ ${odds} ? ${amount} PRIZM`;
}

function renderMeta(label, value) {
  return `
    <div class="operator-meta">
      <div class="operator-meta-label">${escapeHtml(label)}</div>
      <div class="operator-meta-value">${escapeHtml(value || '?')}</div>
    </div>
  `;
}

function labelStatus(status) {
  const value = String(status || '').trim().toLowerCase();
  const labels = {
    accepted: 'Accepted',
    rejected: 'Rejected',
    won: 'Won',
    lost: 'Lost',
    refund_pending: 'Refund pending',
    refunded: 'Refunded',
    paid: 'Paid',
    awaiting_payment: 'Awaiting payment',
    expired: 'Expired',
    pending: 'Pending',
  };
  return labels[value] || (value || 'Unknown');
}

function labelOutcome(outcome) {
  const value = String(outcome || '').trim().toUpperCase();
  const labels = {
    P1: 'P1',
    '1': 'P1',
    X: 'X',
    P2: 'P2',
    '2': 'P2',
    '1X': '1X',
    '12': '12',
    X2: 'X2',
  };
  return labels[value] || value || '?';
}

function labelMatchState(state) {
  const value = String(state || '').trim().toLowerCase();
  const labels = {
    finished: 'Finished',
    live: 'Live',
    imminent: 'Starts < 15 min',
    post_start: 'Started',
    scheduled: 'Before start',
    unknown: 'Unknown',
  };
  return labels[value] || (value || 'Unknown');
}

function labelAuditEvent(value) {
  const eventType = String(value || '').trim().toLowerCase();
  const labels = {
    bet_accepted: 'Bet accepted',
    bet_rejected: 'Bet rejected',
    bet_won: 'Bet won',
    bet_lost: 'Bet lost',
    bet_paid: 'Payout sent',
  };
  return labels[eventType] || (eventType || 'Event');
}

function labelRejectReason(reason) {
  const value = String(reason || '').trim().toUpperCase();
  const labels = {
    INVALID_INTENT: 'Intent code not found',
    DUST_DONATION: 'Amount is below the minimum bet',
    SENDER_MISMATCH: 'Sender wallet does not match the issued coupon',
    INTENT_EXPIRED: 'Coupon expired',
    MATCH_NOT_FOUND: 'Match not found in the current cache',
    LIVE_DISABLED: 'Live bets are disabled in the public version',
    MATCH_ALREADY_STARTED: 'The match has already started',
    LATE_BET: 'The transfer arrived after the safe acceptance window',
  };
  return labels[value] || value || 'Rejected';
}

function resolveStatusTone(status) {
  const value = String(status || '').trim().toLowerCase();
  if (value === 'accepted' || value === 'won' || value === 'paid') return 'good';
  if (value === 'rejected' || value === 'lost' || value === 'expired') return 'bad';
  if (value === 'refund_pending' || value === 'refunded') return 'warn';
  return 'neutral';
}

function resolveMatchStateTone(state) {
  const value = String(state || '').trim().toLowerCase();
  if (value === 'finished') return 'good';
  if (value === 'live' || value === 'imminent' || value === 'post_start') return 'warn';
  return 'neutral';
}

function resolveAuditTone(eventType, status) {
  const event = String(eventType || '').trim().toLowerCase();
  if (event === 'bet_rejected' || event === 'bet_lost') return 'bad';
  if (event === 'bet_accepted' || event === 'bet_won' || event === 'bet_paid') return 'good';
  return resolveStatusTone(status);
}

function cleanText(value) {
  return String(value || '')
    .replaceAll('\u0432\u0402\u201d', '?')
    .replaceAll('\u0432\u0402\u045e', '?')
    .replaceAll('\u0420\u045f1', 'P1')
    .replaceAll('\u0420\u045f2', 'P2')
    .replaceAll('\u0432\u0402\u00a6', '?')
    .trim();
}

function formatNumber(value) {
  const number = Number(value || 0);
  return Number.isFinite(number)
    ? number.toLocaleString('en-US', { maximumFractionDigits: 2 })
    : '0';
}

function formatDate(value) {
  if (!value) return '?';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('en-US', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/`/g, '&#96;');
}

document.addEventListener('DOMContentLoaded', init);
