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
  stats: null,
  meta: null,
  generatedAt: '',
  timer: null,
  message: '',
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
    renderStatus(state.autoRefresh ? 'Автообновление включено.' : 'Автообновление выключено.', 'neutral');
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
      const value = copyButton.getAttribute('data-copy') || '';
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        renderStatus(`Скопировано: ${value}`, 'good');
      } catch {
        renderStatus('Не удалось скопировать значение в буфер обмена.', 'warn');
      }
      return;
    }

    const paidButton = event.target.closest('[data-mark-paid]');
    if (paidButton) {
      await handleMarkPaid(paidButton);
    }
  });
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
    state.stats = null;
    renderStatus('Укажите API base. Для локальной проверки обычно используется http://127.0.0.1:8081.', 'warn');
    render();
    return;
  }

  if (window.location.protocol === 'https:' && state.apiBase.startsWith('http://127.0.0.1')) {
    renderStatus('HTTPS-страница не может безопасно читать локальный HTTP API. Откройте панель локально или используйте HTTPS API.', 'bad');
    return;
  }

  state.loading = true;
  renderStatus('Загружаем операторский поток...', 'neutral');
  render();

  try {
    const url = new URL(`${state.apiBase}/api/admin/feed`);
    url.searchParams.set('limit', '80');
    if (state.query) url.searchParams.set('q', state.query);
    if (state.status) url.searchParams.set('status', state.status);

    const headers = {};
    if (state.adminKey) headers['X-Admin-Key'] = state.adminKey;

    const response = await fetch(url.toString(), { headers });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `API returned ${response.status}`);
    }

    state.items = Array.isArray(payload.items) ? payload.items : [];
    state.stats = payload.stats || null;
    state.meta = payload.meta || null;
    state.generatedAt = payload.generated_at || '';
    renderStatus(buildSuccessMessage(), 'good');
  } catch (error) {
    state.items = [];
    state.stats = null;
    state.meta = null;
    renderStatus(error.message || 'Не удалось загрузить операторский поток.', 'bad');
  } finally {
    state.loading = false;
    render();
  }
}

function buildSuccessMessage() {
  if (state.meta && state.meta.db_configured === false) {
    return state.meta.message || 'Supabase не настроен: поток пока пустой.';
  }
  const keyNote = state.meta?.admin_key_required ? 'Admin key требуется.' : 'Admin key не требуется.';
  return `Поток обновлён. ${keyNote}`;
}

async function handleMarkPaid(button) {
  const txId = button.getAttribute('data-mark-paid') || '';
  const payoutAmount = Number(button.getAttribute('data-payout') || 0);
  if (!txId) return;
  if (!state.apiBase || !state.adminKey) {
    renderStatus('Для выплаты нужны API base и admin key.', 'warn');
    return;
  }

  const payoutTxId = window.prompt('Укажите payout TX ID. Поле можно оставить пустым, если перевод будет зафиксирован позже.', '') || '';
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
    renderStatus(`Ставка ${txId} отмечена как выплаченная.`, 'good');
    await fetchFeed();
  } catch (error) {
    renderStatus(error.message || 'Не удалось отметить выплату.', 'bad');
  } finally {
    button.disabled = false;
  }
}

function renderStatus(message, tone) {
  state.message = String(message || '');
  dom.operatorStatus.textContent = state.message || 'Ожидание подключения к API.';
  dom.operatorStatus.dataset.tone = tone || 'neutral';
}

function render() {
  renderStats();
  renderFeedMeta();
  renderFeed();
}

function renderStats() {
  const stats = state.stats;
  if (!stats) {
    dom.statsGrid.innerHTML = [
      buildStatCard('Ставок в ленте', '0'),
      buildStatCard('Принято', '0'),
      buildStatCard('К выплате', '0'),
      buildStatCard('Выплачено', '0'),
      buildStatCard('Оборот', '0 PRIZM'),
    ].join('');
    return;
  }

  dom.statsGrid.innerHTML = [
    buildStatCard('Ставок в ленте', formatNumber(stats.total_items)),
    buildStatCard('Принято', formatNumber(stats.accepted_count)),
    buildStatCard('К выплате', formatNumber(stats.to_payout_count ?? stats.won_count ?? 0)),
    buildStatCard('Выплачено', formatNumber(stats.paid_count ?? 0)),
    buildStatCard('Оборот', `${formatNumber(stats.turnover_prizm)} PRIZM`),
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
  if (state.loading) parts.push('Загрузка...');
  if (state.generatedAt) parts.push(`Обновлено ${formatDate(state.generatedAt)}`);
  if (state.items.length) parts.push(`${state.items.length} записей`);
  const liveItems = state.items.filter((item) => item.match_state === 'live').length;
  const payoutItems = state.items.filter((item) => item.status === 'won').length;
  if (liveItems) parts.push(`LIVE: ${liveItems}`);
  if (payoutItems) parts.push(`К выплате: ${payoutItems}`);
  dom.feedMeta.textContent = parts.join(' - ') || 'Поток ещё не загружен.';
}

function renderFeed() {
  if (!state.items.length) {
    dom.feedList.innerHTML = `
      <div class="operator-empty">
        <strong>Ставок пока нет.</strong><br>
        Когда listener или API найдут подтверждённые ставки, они появятся в этой ленте.
      </div>
    `;
    return;
  }

  dom.feedList.innerHTML = state.items.map(renderCard).join('');
}

function renderCard(item) {
  const rejectBlock = item.reject_label
    ? `<div class="operator-reject">${escapeHtml(item.reject_label)}</div>`
    : '';

  const payoutAction = item.status === 'won'
    ? `<button class="operator-chip" type="button" data-mark-paid="${escapeAttr(item.tx_id || '')}" data-payout="${escapeAttr(item.potential_payout_prizm || 0)}">Отметить выплату</button>`
    : '';

  const payoutTxChip = item.payout_tx_id
    ? `<button class="operator-chip" type="button" data-copy="${escapeAttr(item.payout_tx_id)}">Payout TX</button>`
    : '';

  return `
    <article class="operator-card">
      <div class="operator-card-head">
        <div>
          <div class="operator-badges">
            <span class="operator-badge" data-tone="${escapeHtml(item.status_tone || 'neutral')}">${escapeHtml(item.status_label || item.status || '?')}</span>
            <span class="operator-badge" data-tone="${escapeHtml(item.match_state_tone || 'neutral')}">${escapeHtml(item.match_state_label || 'Матч')}</span>
          </div>
          <h3 class="operator-card-title">${escapeHtml(item.match_label || 'Матч без расшифровки')}</h3>
          <p class="operator-card-copy">${escapeHtml(item.operator_summary || '')}</p>
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
        ${renderMeta('Кошелёк', item.sender_wallet || '?')}
        ${renderMeta('Исход', `${item.outcome_label || '?'} @ ${item.odds_label || '0.00'}`)}
        ${renderMeta('Сумма', `${formatNumber(item.amount_prizm)} PRIZM`)}
        ${renderMeta('Потенциал', `${formatNumber(item.potential_payout_prizm)} PRIZM`)}
        ${renderMeta('Время', formatDate(item.block_timestamp || item.created_at))}
      </div>
      ${rejectBlock}
    </article>
  `;
}

function renderMeta(label, value) {
  return `
    <div class="operator-meta">
      <div class="operator-meta-label">${escapeHtml(label)}</div>
      <div class="operator-meta-value">${escapeHtml(value || '?')}</div>
    </div>
  `;
}

function formatNumber(value) {
  const number = Number(value || 0);
  return Number.isFinite(number)
    ? number.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
    : '0';
}

function formatDate(value) {
  if (!value) return '?';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('ru-RU', {
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
