const STORAGE_KEY = 'prizmbet_operator_console_v3';
const AUTO_REFRESH_MS = 20000;

const state = {
  apiBase: '',
  sessionToken: '',
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
  bootstrapInfo: null,
  currentUser: null,
  sessionInfo: null,
  users: [],
};

const dom = {};

function init() {
  cacheDom();
  bindEvents();
  restoreState();
  syncInputs();
  render();
  syncAutoRefresh();
  if (state.apiBase) {
    connectFlow();
  }
}

function cacheDom() {
  dom.apiBaseInput = document.getElementById('apiBaseInput');
  dom.connectBtn = document.getElementById('connectBtn');
  dom.refreshBtn = document.getElementById('refreshBtn');
  dom.autoRefreshToggle = document.getElementById('autoRefreshToggle');
  dom.operatorStatus = document.getElementById('operatorStatus');
  dom.authStateMeta = document.getElementById('authStateMeta');

  dom.bootstrapSection = document.getElementById('bootstrapSection');
  dom.ownerEmailInput = document.getElementById('ownerEmailInput');
  dom.ownerLoginInput = document.getElementById('ownerLoginInput');
  dom.bootstrapPasswordInput = document.getElementById('bootstrapPasswordInput');
  dom.bootstrapKeyInput = document.getElementById('bootstrapKeyInput');
  dom.bootstrapBtn = document.getElementById('bootstrapBtn');

  dom.loginSection = document.getElementById('loginSection');
  dom.identityInput = document.getElementById('identityInput');
  dom.passwordInput = document.getElementById('passwordInput');
  dom.loginBtn = document.getElementById('loginBtn');

  dom.sessionSection = document.getElementById('sessionSection');
  dom.sessionUserMeta = document.getElementById('sessionUserMeta');
  dom.sessionExpiresMeta = document.getElementById('sessionExpiresMeta');
  dom.logoutBtn = document.getElementById('logoutBtn');

  dom.userManagementSection = document.getElementById('userManagementSection');
  dom.newUserLoginInput = document.getElementById('newUserLoginInput');
  dom.newUserEmailInput = document.getElementById('newUserEmailInput');
  dom.newUserPasswordInput = document.getElementById('newUserPasswordInput');
  dom.newUserRoleInput = document.getElementById('newUserRoleInput');
  dom.createUserBtn = document.getElementById('createUserBtn');
  dom.userList = document.getElementById('userList');

  dom.statsGrid = document.getElementById('statsGrid');
  dom.queryInput = document.getElementById('queryInput');
  dom.statusFilter = document.getElementById('statusFilter');
  dom.feedMeta = document.getElementById('feedMeta');
  dom.feedList = document.getElementById('feedList');
  dom.auditMeta = document.getElementById('auditMeta');
  dom.auditList = document.getElementById('auditList');
}

function bindEvents() {
  dom.connectBtn.addEventListener('click', async () => {
    state.apiBase = normalizeApiBase(dom.apiBaseInput.value);
    persistState();
    await connectFlow();
  });

  dom.refreshBtn.addEventListener('click', async () => {
    await refreshCurrentView();
  });

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
    debounceId = setTimeout(() => {
      if (state.currentUser) fetchFeed();
    }, 280);
  });

  dom.statusFilter.addEventListener('change', () => {
    state.status = dom.statusFilter.value;
    persistState();
    if (state.currentUser) fetchFeed();
  });

  dom.bootstrapBtn.addEventListener('click', async () => {
    await handleBootstrap();
  });

  dom.loginBtn.addEventListener('click', async () => {
    await handleLogin();
  });

  dom.logoutBtn.addEventListener('click', async () => {
    await handleLogout();
  });

  dom.createUserBtn.addEventListener('click', async () => {
    await handleCreateUser();
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
    if (copyButton) {
      await copyValue(copyButton.getAttribute('data-copy') || '');
    }
  });

  dom.userList.addEventListener('click', async (event) => {
    const toggleButton = event.target.closest('[data-toggle-user]');
    if (toggleButton) {
      await handleToggleUser(toggleButton);
    }
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
    state.sessionToken = String(saved.sessionToken || '');
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
    sessionToken: state.sessionToken,
    query: state.query,
    status: state.status,
    autoRefresh: state.autoRefresh,
  }));
}

function syncInputs() {
  dom.apiBaseInput.value = state.apiBase;
  dom.queryInput.value = state.query;
  dom.statusFilter.value = state.status;
  dom.autoRefreshToggle.checked = state.autoRefresh;

  if (state.bootstrapInfo?.owner_email_hint) {
    dom.ownerEmailInput.placeholder = state.bootstrapInfo.owner_email_hint;
  }
  if (!dom.ownerLoginInput.value && state.bootstrapInfo?.owner_login) {
    dom.ownerLoginInput.value = state.bootstrapInfo.owner_login;
  }
}

function syncAutoRefresh() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
  if (state.autoRefresh) {
    state.timer = setInterval(() => {
      if (!state.loading && state.currentUser) {
        fetchFeed();
      }
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

function buildAuthHeaders() {
  const headers = {};
  if (state.sessionToken) {
    headers['X-Admin-Session'] = state.sessionToken;
  }
  return headers;
}

async function connectFlow() {
  if (!state.apiBase) {
    renderStatus('Set API base first.', 'warn');
    render();
    return;
  }
  renderStatus('Checking operator access...', 'neutral');
  await fetchBootstrapState();
  if (state.sessionToken) {
    const ok = await loadMe();
    if (ok) {
      await fetchFeed();
      return;
    }
  }
  render();
}

async function fetchBootstrapState() {
  if (!state.apiBase) return;
  try {
    const response = await fetch(`${state.apiBase}/api/admin/bootstrap-state`);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Bootstrap API returned ${response.status}`);
    }
    state.bootstrapInfo = payload;
    syncInputs();
  } catch (error) {
    state.bootstrapInfo = null;
    renderStatus(error.message || 'Failed to read bootstrap state.', 'bad');
  }
}

async function loadMe() {
  if (!state.apiBase || !state.sessionToken) {
    clearSession();
    return false;
  }
  try {
    const response = await fetch(`${state.apiBase}/api/admin/me`, {
      headers: buildAuthHeaders(),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Session API returned ${response.status}`);
    }
    state.currentUser = payload.user || null;
    state.sessionInfo = payload.session || null;
    persistState();
    return true;
  } catch (error) {
    clearSession();
    renderStatus(error.message || 'Admin session is invalid.', 'warn');
    return false;
  }
}

function clearSession() {
  state.sessionToken = '';
  state.currentUser = null;
  state.sessionInfo = null;
  state.users = [];
  persistState();
}

async function refreshCurrentView() {
  if (!state.apiBase) {
    renderStatus('Set API base first.', 'warn');
    return;
  }
  await fetchBootstrapState();
  if (state.sessionToken) {
    const ok = await loadMe();
    if (ok) {
      await fetchFeed();
      return;
    }
  }
  render();
}

async function handleBootstrap() {
  if (!state.apiBase) {
    renderStatus('Set API base first.', 'warn');
    return;
  }
  const email = dom.ownerEmailInput.value.trim();
  const login = dom.ownerLoginInput.value.trim();
  const password = dom.bootstrapPasswordInput.value;
  const bootstrapKey = dom.bootstrapKeyInput.value.trim();
  if (!email || !login || !password || !bootstrapKey) {
    renderStatus('Owner email, login, password and bootstrap key are required.', 'warn');
    return;
  }

  dom.bootstrapBtn.disabled = true;
  try {
    const response = await fetch(`${state.apiBase}/api/admin/bootstrap`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': bootstrapKey,
      },
      body: JSON.stringify({ email, login, password, bootstrap_key: bootstrapKey }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Bootstrap API returned ${response.status}`);
    }
    state.sessionToken = payload.session?.token || '';
    state.currentUser = payload.user || null;
    state.sessionInfo = payload.session || null;
    persistState();
    dom.bootstrapPasswordInput.value = '';
    dom.bootstrapKeyInput.value = '';
    await fetchBootstrapState();
    renderStatus('Owner account created. Session is active.', 'good');
    await fetchFeed();
  } catch (error) {
    renderStatus(error.message || 'Failed to bootstrap owner account.', 'bad');
  } finally {
    dom.bootstrapBtn.disabled = false;
    render();
  }
}

async function handleLogin() {
  if (!state.apiBase) {
    renderStatus('Set API base first.', 'warn');
    return;
  }
  const identity = dom.identityInput.value.trim();
  const password = dom.passwordInput.value;
  if (!identity || !password) {
    renderStatus('Login/email and password are required.', 'warn');
    return;
  }

  dom.loginBtn.disabled = true;
  try {
    const response = await fetch(`${state.apiBase}/api/admin/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ identity, password }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Login API returned ${response.status}`);
    }
    state.sessionToken = payload.session?.token || '';
    state.currentUser = payload.user || null;
    state.sessionInfo = payload.session || null;
    persistState();
    dom.passwordInput.value = '';
    renderStatus(`Logged in as ${state.currentUser?.login || 'operator'}.`, 'good');
    await fetchFeed();
  } catch (error) {
    renderStatus(error.message || 'Failed to log in.', 'bad');
  } finally {
    dom.loginBtn.disabled = false;
    render();
  }
}

async function handleLogout() {
  if (!state.apiBase || !state.sessionToken) {
    clearSession();
    render();
    return;
  }

  dom.logoutBtn.disabled = true;
  try {
    await fetch(`${state.apiBase}/api/admin/logout`, {
      method: 'POST',
      headers: buildAuthHeaders(),
    });
  } catch {
  } finally {
    clearSession();
    dom.logoutBtn.disabled = false;
    renderStatus('Session closed.', 'neutral');
    render();
  }
}

async function handleCreateUser() {
  if (state.currentUser?.role !== 'super_admin') {
    renderStatus('Only the super admin can create users.', 'warn');
    return;
  }

  const login = dom.newUserLoginInput.value.trim();
  const email = dom.newUserEmailInput.value.trim();
  const password = dom.newUserPasswordInput.value;
  const role = dom.newUserRoleInput.value;
  if (!login || !password) {
    renderStatus('Login and password are required for a new user.', 'warn');
    return;
  }

  dom.createUserBtn.disabled = true;
  try {
    const response = await fetch(`${state.apiBase}/api/admin/users`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({ login, email, password, role }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Create user API returned ${response.status}`);
    }
    dom.newUserLoginInput.value = '';
    dom.newUserEmailInput.value = '';
    dom.newUserPasswordInput.value = '';
    dom.newUserRoleInput.value = 'operator';
    renderStatus(`User ${payload.user?.login || login} created.`, 'good');
    await loadUsers();
  } catch (error) {
    renderStatus(error.message || 'Failed to create user.', 'bad');
  } finally {
    dom.createUserBtn.disabled = false;
    render();
  }
}

async function handleToggleUser(button) {
  const userId = button.getAttribute('data-toggle-user') || '';
  const nextActive = button.getAttribute('data-next-active') === 'true';
  if (!userId) return;
  button.disabled = true;
  try {
    const response = await fetch(`${state.apiBase}/api/admin/users/${encodeURIComponent(userId)}/set-active`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...buildAuthHeaders(),
      },
      body: JSON.stringify({ is_active: nextActive }),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Set-active API returned ${response.status}`);
    }
    renderStatus(`User ${payload.user?.login || userId} updated.`, 'good');
    await loadUsers();
  } catch (error) {
    renderStatus(error.message || 'Failed to update user state.', 'bad');
  } finally {
    button.disabled = false;
  }
}

async function loadUsers() {
  if (state.currentUser?.role !== 'super_admin') {
    state.users = [];
    render();
    return;
  }
  try {
    const response = await fetch(`${state.apiBase}/api/admin/users`, {
      headers: buildAuthHeaders(),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || `Users API returned ${response.status}`);
    }
    state.users = Array.isArray(payload.users) ? payload.users : [];
  } catch (error) {
    renderStatus(error.message || 'Failed to load admin users.', 'bad');
  }
}

async function fetchFeed() {
  if (!state.apiBase) {
    renderStatus('Set API base first.', 'warn');
    render();
    return;
  }
  if (!state.sessionToken) {
    renderStatus('Log in first.', 'warn');
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

    const headers = buildAuthHeaders();
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
    state.currentUser = feedPayload.meta?.current_user || state.currentUser;

    if (state.currentUser?.role === 'super_admin') {
      await loadUsers();
    } else {
      state.users = [];
    }

    renderStatus(buildSuccessMessage(), 'good');
  } catch (error) {
    if (String(error.message || '').toLowerCase().includes('invalid or expired') || String(error.message || '').toLowerCase().includes('session')) {
      clearSession();
    }
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
  const mirrorNote = state.auditMeta?.sheets_mirror_enabled ? 'Google Sheets mirror is ON.' : 'Google Sheets mirror is OFF.';
  const userNote = state.currentUser ? `Logged in as ${state.currentUser.login} (${labelRole(state.currentUser.role)}).` : 'No active operator session.';
  return `${userNote} ${mirrorNote}`;
}

async function handleMarkPaid(button) {
  const txId = button.getAttribute('data-mark-paid') || '';
  const payoutAmount = Number(button.getAttribute('data-payout') || 0);
  if (!txId) return;
  if (!state.apiBase || !state.sessionToken) {
    renderStatus('Log in first to mark payouts.', 'warn');
    return;
  }

  const payoutTxId = window.prompt('Enter payout TX ID. Leave empty if the transfer will be added later.', '') || '';
  button.disabled = true;
  try {
    const response = await fetch(`${state.apiBase}/api/admin/bets/${encodeURIComponent(txId)}/mark-paid`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...buildAuthHeaders(),
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
  syncInputs();
  renderAuthState();
  renderUsers();
  renderStats();
  renderFeedMeta();
  renderFeed();
  renderAuditMeta();
  renderAudit();
}

function renderAuthState() {
  const info = state.bootstrapInfo;
  if (!state.apiBase) {
    dom.authStateMeta.textContent = 'Set API base and connect.';
    setHidden(dom.bootstrapSection, true);
    setHidden(dom.loginSection, true);
    setHidden(dom.sessionSection, true);
    setHidden(dom.userManagementSection, true);
    return;
  }

  if (!info) {
    dom.authStateMeta.textContent = 'Connect to inspect the operator auth state.';
    setHidden(dom.bootstrapSection, true);
    setHidden(dom.loginSection, true);
    setHidden(dom.sessionSection, true);
    setHidden(dom.userManagementSection, true);
    return;
  }

  if (!info.db_configured) {
    dom.authStateMeta.textContent = 'Database is not configured. Operator auth is unavailable.';
    setHidden(dom.bootstrapSection, true);
    setHidden(dom.loginSection, true);
    setHidden(dom.sessionSection, true);
    setHidden(dom.userManagementSection, true);
    return;
  }

  if (!info.has_admin_users) {
    dom.authStateMeta.textContent = info.bootstrap_allowed
      ? `Bootstrap pending. Owner login: ${info.owner_login}. Owner email hint: ${info.owner_email_hint || 'n/a'}.`
      : 'Bootstrap is blocked. Check ADMIN_VIEW_KEY and migration state.';
    setHidden(dom.bootstrapSection, !info.bootstrap_allowed);
    setHidden(dom.loginSection, true);
    setHidden(dom.sessionSection, true);
    setHidden(dom.userManagementSection, true);
    return;
  }

  if (!state.currentUser) {
    dom.authStateMeta.textContent = 'Operator accounts exist. Log in to continue.';
    setHidden(dom.bootstrapSection, true);
    setHidden(dom.loginSection, false);
    setHidden(dom.sessionSection, true);
    setHidden(dom.userManagementSection, true);
    return;
  }

  dom.authStateMeta.textContent = `Session active: ${state.currentUser.login} (${labelRole(state.currentUser.role)}).`;
  dom.sessionUserMeta.textContent = `${state.currentUser.login} (${labelRole(state.currentUser.role)})`;
  dom.sessionExpiresMeta.textContent = formatDate(state.sessionInfo?.expires_at);
  setHidden(dom.bootstrapSection, true);
  setHidden(dom.loginSection, true);
  setHidden(dom.sessionSection, false);
  setHidden(dom.userManagementSection, state.currentUser.role !== 'super_admin');
}

function renderUsers() {
  if (state.currentUser?.role !== 'super_admin') {
    dom.userList.innerHTML = '';
    return;
  }
  if (!state.users.length) {
    dom.userList.innerHTML = `
      <div class="operator-empty">
        <strong>No additional operators yet.</strong><br>
        Create the first assigned operator here.
      </div>
    `;
    return;
  }

  dom.userList.innerHTML = state.users.map(renderUserCard).join('');
}

function renderUserCard(user) {
  const isOwner = String(user.role || '') === 'super_admin';
  const canToggle = !isOwner;
  const nextActive = !Boolean(user.is_active);
  const toggleLabel = user.is_active ? 'Disable' : 'Enable';

  return `
    <article class="operator-card operator-user-card">
      <div class="operator-card-head">
        <div>
          <div class="operator-badges">
            <span class="operator-badge" data-tone="${user.is_active ? 'good' : 'bad'}">${user.is_active ? 'Active' : 'Disabled'}</span>
            <span class="operator-badge" data-tone="neutral">${escapeHtml(labelRole(user.role))}</span>
            ${isOwner ? '<span class="operator-badge" data-tone="warn">Owner</span>' : ''}
          </div>
          <h3 class="operator-card-title">${escapeHtml(user.login || 'Unknown')}</h3>
          <p class="operator-card-copy">${escapeHtml(user.email || 'No email assigned')}</p>
        </div>
        <div class="operator-actions">
          ${canToggle ? `<button class="operator-chip" type="button" data-toggle-user="${escapeAttr(user.id)}" data-next-active="${nextActive ? 'true' : 'false'}">${toggleLabel}</button>` : ''}
        </div>
      </div>
      <div class="operator-card-grid">
        ${renderMeta('Created', formatDate(user.created_at))}
        ${renderMeta('Last login', formatDate(user.last_login_at))}
        ${renderMeta('User ID', String(user.id || '-'))}
      </div>
    </article>
  `;
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
  dom.feedMeta.textContent = parts.join(' • ') || 'Feed not loaded yet.';
}

function renderAuditMeta() {
  const parts = [];
  if (state.loading) parts.push('Loading...');
  if (state.auditItems.length) parts.push(`${state.auditItems.length} events`);
  parts.push(state.auditMeta?.sheets_mirror_enabled ? 'Google Sheets: ON' : 'Google Sheets: OFF');
  if (state.auditMeta?.audit_schema_ready === false && state.auditMeta?.message) parts.push(state.auditMeta.message);
  dom.auditMeta.textContent = parts.join(' • ') || 'Audit log not loaded yet.';
}

function renderFeed() {
  if (!state.currentUser) {
    dom.feedList.innerHTML = `
      <div class="operator-empty">
        <strong>No active session.</strong><br>
        Log in to load bets and payouts.
      </div>
    `;
    return;
  }
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
  if (!state.currentUser) {
    dom.auditList.innerHTML = `
      <div class="operator-empty">
        <strong>No active session.</strong><br>
        Log in to inspect audit events.
      </div>
    `;
    return;
  }
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
  const payoutAction = item.status === 'won' && (state.currentUser?.role === 'super_admin' || state.currentUser?.role === 'finance')
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
        ${renderMeta('Intent', item.intent_hash || '-')}
        ${renderMeta('Wallet', item.sender_wallet || '-')}
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
  const rejectBlock = payload.reject_reason
    ? `<div class="operator-reject">${escapeHtml(labelRejectReason(payload.reject_reason))}</div>`
    : '';
  const title = cleanText(payload.match_label) || labelAuditEvent(eventType);

  return `
    <article class="operator-card operator-card--audit">
      <div class="operator-card-head">
        <div>
          <div class="operator-badges">
            <span class="operator-badge" data-tone="${escapeHtml(resolveAuditTone(eventType, status))}">${escapeHtml(labelAuditEvent(eventType))}</span>
            <span class="operator-badge" data-tone="${escapeHtml(resolveStatusTone(status))}">${escapeHtml(labelStatus(status || 'admin'))}</span>
          </div>
          <h3 class="operator-card-title">${escapeHtml(title)}</h3>
          <p class="operator-card-copy">${escapeHtml(buildAuditSummary(payload, item))}</p>
        </div>
        <div class="operator-actions">
          ${payload.intent_hash || item.intent_hash ? `<button class="operator-chip" type="button" data-copy="${escapeAttr(payload.intent_hash || item.intent_hash || '')}">Intent</button>` : ''}
          ${payload.tx_id || item.tx_id ? `<button class="operator-chip" type="button" data-copy="${escapeAttr(payload.tx_id || item.tx_id || '')}">TX</button>` : ''}
        </div>
      </div>
      <div class="operator-card-grid">
        ${renderMeta('Event type', labelAuditEvent(eventType))}
        ${renderMeta('Actor', buildActorLabel(payload.actor))}
        ${renderMeta('Amount', `${formatNumber(payload.amount_prizm || item.amount_prizm)} PRIZM`)}
        ${renderMeta('Match state', labelMatchState(payload.match_state || ''))}
        ${renderMeta('Time', formatDate(item.created_at || payload.created_at))}
        ${renderMeta('Extra', summarizeExtra(payload.extra))}
      </div>
      ${rejectBlock}
    </article>
  `;
}

function buildFeedSummary(item) {
  const match = cleanText(item.match_label) || `Match #${item.match_id || '?'}`;
  const outcome = labelOutcome(item.outcome);
  const odds = item.odds_label || formatNumber(item.odds_fixed);
  const amount = formatNumber(item.amount_prizm);
  return `${match} - ${outcome} @ ${odds} - ${amount} PRIZM`;
}

function buildAuditSummary(payload, item) {
  const actor = buildActorLabel(payload.actor);
  if (String(item.event_type || payload.event_type || '').startsWith('admin_')) {
    return actor ? `Operator: ${actor}` : 'Operator-side event';
  }
  const match = cleanText(payload.match_label || item.match_label) || `Match #${payload.match_id || item.match_id || '?'}`;
  const outcome = labelOutcome(payload.outcome || item.outcome || '');
  const odds = payload.odds_fixed ? formatNumber(payload.odds_fixed) : (item.odds_label || formatNumber(item.odds_fixed));
  const amount = formatNumber(payload.amount_prizm || item.amount_prizm);
  return `${match} - ${outcome} @ ${odds} - ${amount} PRIZM`;
}

function renderMeta(label, value) {
  return `
    <div class="operator-meta">
      <div class="operator-meta-label">${escapeHtml(label)}</div>
      <div class="operator-meta-value">${escapeHtml(value || '-')}</div>
    </div>
  `;
}

function buildActorLabel(actor) {
  if (!actor || typeof actor !== 'object') return '-';
  const login = String(actor.login || '').trim();
  const role = labelRole(actor.role || '');
  if (!login && !role) return '-';
  return `${login || 'unknown'} (${role || 'unknown'})`;
}

function summarizeExtra(extra) {
  if (!extra || typeof extra !== 'object') return '-';
  const parts = Object.entries(extra).slice(0, 3).map(([key, value]) => `${key}: ${value}`);
  return parts.join(' | ') || '-';
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
    admin: 'Admin',
  };
  return labels[value] || (value || 'Unknown');
}

function labelRole(role) {
  const value = String(role || '').trim().toLowerCase();
  const labels = {
    super_admin: 'Super admin',
    operator: 'Operator',
    finance: 'Finance',
    viewer: 'Viewer',
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
  return labels[value] || value || '-';
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
    admin_bootstrap_completed: 'Owner bootstrap completed',
    admin_login: 'Operator login',
    admin_logout: 'Operator logout',
    admin_user_created: 'Operator user created',
    admin_user_state_changed: 'Operator user state changed',
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
  if (event === 'bet_accepted' || event === 'bet_won' || event === 'bet_paid' || event.startsWith('admin_')) return 'good';
  return resolveStatusTone(status);
}

function cleanText(value) {
  return String(value || '').trim();
}

function formatNumber(value) {
  const number = Number(value || 0);
  return Number.isFinite(number)
    ? number.toLocaleString('en-US', { maximumFractionDigits: 2 })
    : '0';
}

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString('en-US', {
    timeZone: 'Europe/Moscow',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function setHidden(node, hidden) {
  if (!node) return;
  node.classList.toggle('operator-hidden', hidden);
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
