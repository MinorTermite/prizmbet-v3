// ===== КОНФИГУРАЦИЯ =====
const AUTO_REFRESH_MS = 5 * 60 * 1000;
const LS_CACHE_KEY = 'prizmbet_matches_cache';
const LS_FULL_KEY  = 'prizmbet_matches_full_cache';

// ===== CACHE HELPERS =====
function _getLS(key) {
    try { const r = localStorage.getItem(key); return r ? JSON.parse(r) : null; }
    catch { return null; }
}
function _setLS(key, data) {
    try { localStorage.setItem(key, JSON.stringify(data)); } catch { }
}

function fmtTime(ts) {
    if (!ts) return '—';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString('ru-RU', { timeZone: 'Europe/Moscow', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function showStatus(ts, extra) {
    const el = document.getElementById('lastUpdate');
    if (!el) return;
    el.innerHTML = `Обновлено: ${fmtTime(ts)}${extra || ''}`;
}

function showShimmer() {
    const content = document.getElementById('content');
    if (!content) return;
    let html = '';
    for (let i = 0; i < 6; i++) html += '<div class="skeleton-card shimmer"></div>';
    content.innerHTML = html;
}

function _showLoadError() {
    const content = document.getElementById('content');
    if (!content || !content.querySelector('.shimmer')) return; // уже есть данные
    content.innerHTML = `
        <div style="text-align:center;padding:60px 20px;color:var(--text-tertiary,#888)">
            <div style="font-size:2.5rem;margin-bottom:14px">📡</div>
            <p style="margin-bottom:6px;font-size:1rem;color:var(--text-secondary,#ccc)">Не удалось загрузить матчи</p>
            <p style="margin-bottom:22px;font-size:.85rem;opacity:.7">Проверьте подключение к интернету</p>
            <button onclick="loadData()" style="background:#6366f1;color:#fff;border:none;padding:10px 28px;border-radius:8px;cursor:pointer;font-size:.95rem;font-weight:600;letter-spacing:.02em">🔄 Повторить</button>
        </div>`;
}

// ===== CACHE-BUST: round to 10-minute windows (CDN/browser cache friendly) =====
function cacheBust() { return Math.floor(Date.now() / 600000); }

// ===== FETCH HELPER с таймаутом 10 сек =====
async function _fetchJson(url, timeoutMs = 10000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const r = await fetch(url, { signal: controller.signal });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    } finally {
        clearTimeout(timer);
    }
}

// ===== MAIN LOAD =====
// mode: 'fast' (default) = matches-today.json  |  'full' = matches.json
async function loadData(mode) {
    const isFull = mode === 'full';
    const cacheKey = isFull ? LS_FULL_KEY : LS_CACHE_KEY;

    // 1. Показываем кэш мгновенно, или шиммер при первом запуске
    const cached = _getLS(cacheKey) || _getLS(LS_CACHE_KEY);
    let shimmerTimer = null;

    if (cached?.matches?.length) {
        if (typeof renderMatches === 'function') renderMatches(cached.matches);
        showStatus(cached.last_update, ' <span style="font-size:.75em;opacity:.6">(кэш)</span>');
    } else {
        showShimmer();
        // Fallback: если данные не пришли за 10 сек — показываем кнопку "Повторить"
        shimmerTimer = setTimeout(_showLoadError, 10000);
    }

    // 2. Запрашиваем свежий JSON
    const file = isFull ? 'matches.json' : 'matches-today.json';
    let data = null;
    try {
        data = await _fetchJson(`${file}?v=${cacheBust()}`);
    } catch (e) { console.warn(`[api] ${file} fetch:`, e.message); }

    // Отменяем таймер шиммера — данные либо пришли, либо нет
    if (shimmerTimer) clearTimeout(shimmerTimer);

    if (data?.matches?.length) {
        _setLS(cacheKey, data);
        if (typeof renderMatches === 'function') renderMatches(data.matches);
        if (data.total) {
            const el = document.getElementById('totalMatches');
            if (el) el.textContent = data.total;
        }
        const label = isFull ? ' <span style="font-size:.75em;opacity:.6">(все)</span>'
                              : ' <span style="font-size:.75em;opacity:.6">(сегодня)</span>';
        showStatus(data.last_update, label);
    } else if (!cached?.matches?.length) {
        // Нет кэша И данные не пришли → показываем ошибку сразу
        _showLoadError();
    }
}

// ===== AUTO-REFRESH =====
setInterval(() => { if (document.visibilityState === 'visible') loadData(); }, AUTO_REFRESH_MS);
