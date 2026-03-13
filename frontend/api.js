// ===== CONFIG =====
const AUTO_REFRESH_MS = 5 * 60 * 1000;
const LS_CACHE_KEY = 'prizmbet_matches_cache';
const LS_FULL_KEY = 'prizmbet_matches_full_cache';
const LANG_KEY = 'prizmbet_lang_v1';
const STALE_SNAPSHOT_MS = 8 * 60 * 60 * 1000;

function getLang() {
    return String(localStorage.getItem(LANG_KEY) || 'ru').toLowerCase() === 'en' ? 'en' : 'ru';
}
function getLocale() {
    return getLang() === 'en' ? 'en-US' : 'ru-RU';
}
function getZone() {
    return 'Europe/Moscow';
}
function t(key, vars = {}) {
    const dict = {
        ru: {
            updated: 'Обновлено: {value}',
            cache: 'кэш',
            full: 'полный',
            line: 'линия',
            archive: 'архивный срез',
            loadErrorTitle: 'Не удалось загрузить матчи',
            loadErrorText: 'Проверьте подключение и повторите попытку',
            retry: 'Повторить',
        },
        en: {
            updated: 'Updated: {value}',
            cache: 'cache',
            full: 'full',
            line: 'line',
            archive: 'archived snapshot',
            loadErrorTitle: 'Failed to load matches',
            loadErrorText: 'Check your internet connection',
            retry: 'Retry',
        },
    };
    const table = dict[getLang()];
    return String(table[key] || key).replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ''));
}

function _getLS(key) {
    try { const r = localStorage.getItem(key); return r ? JSON.parse(r) : null; }
    catch { return null; }
}
function _setLS(key, data) {
    try { localStorage.setItem(key, JSON.stringify(data)); } catch { }
}

function parseTimestamp(ts) {
    if (!ts) return null;
    const parsed = new Date(ts);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function buildMeta(data, mode, fromCache) {
    const count = Array.isArray(data?.matches) ? data.matches.length : 0;
    const parsed = parseTimestamp(data?.last_update);
    const ageMs = parsed ? Date.now() - parsed.getTime() : null;
    return {
        mode: mode === 'full' ? 'full' : 'fast',
        file: mode === 'full' ? 'matches.json' : 'matches-today.json',
        source: data?.source || '',
        last_update: data?.last_update || null,
        total: count,
        age_ms: ageMs,
        from_cache: Boolean(fromCache),
        is_stale: typeof ageMs === 'number' && ageMs > STALE_SNAPSHOT_MS,
    };
}

function applyMeta(data, mode, fromCache) {
    const meta = buildMeta(data, mode, fromCache);
    window.__MATCHES_META__ = {
        ...meta,
        isStale: meta.is_stale,
        fromCache: meta.from_cache,
    };
    return window.__MATCHES_META__;
}

function fmtTime(ts) {
    if (!ts) return '?';
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString(getLocale(), { timeZone: getZone(), day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function showStatus(ts, extra) {
    const el = document.getElementById('lastUpdate');
    if (!el) return;
    el.innerHTML = t('updated', { value: fmtTime(ts) }) + (extra || '');
}

function buildStatusFlags(meta, isFull) {
    const flags = [];
    if (meta.fromCache) flags.push(t('cache'));
    flags.push(isFull ? t('full') : t('line'));
    if (meta.isStale) flags.push(t('archive'));
    return ` <span style="font-size:.75em;opacity:.6">(${flags.join(', ')})</span>`;
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
    if (!content || !content.querySelector('.shimmer')) return;
    content.innerHTML = `
        <div style="text-align:center;padding:60px 20px;color:var(--text-tertiary,#888)">
            <div style="font-size:2.5rem;margin-bottom:14px">&#9888;</div>
            <p style="margin-bottom:6px;font-size:1rem;color:var(--text-secondary,#ccc)">${t('loadErrorTitle')}</p>
            <p style="margin-bottom:22px;font-size:.85rem;opacity:.7">${t('loadErrorText')}</p>
            <button onclick="loadData()" style="background:#6366f1;color:#fff;border:none;padding:10px 28px;border-radius:8px;cursor:pointer;font-size:.95rem;font-weight:600;letter-spacing:.02em">${t('retry')}</button>
        </div>`;
}

function cacheBust() { return Math.floor(Date.now() / 600000); }

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

async function loadData(mode) {
    const isFull = mode === 'full';
    const cacheKey = isFull ? LS_FULL_KEY : LS_CACHE_KEY;
    const cached = _getLS(cacheKey) || _getLS(LS_CACHE_KEY);
    let shimmerTimer = null;

    if (cached?.matches?.length) {
        const cachedMeta = applyMeta(cached, mode, true);
        if (typeof renderMatches === 'function') renderMatches(cached.matches);
        showStatus(cached.last_update, buildStatusFlags(cachedMeta, isFull));
    } else {
        showShimmer();
        shimmerTimer = setTimeout(_showLoadError, 10000);
    }

    const file = isFull ? 'matches.json' : 'matches-today.json';
    let data = null;
    try {
        data = await _fetchJson(`${file}?v=${cacheBust()}`);
    } catch (e) {
        console.warn(`[api] ${file} fetch:`, e.message);
    }

    if (shimmerTimer) clearTimeout(shimmerTimer);

    if (data?.matches?.length) {
        const liveMeta = applyMeta(data, mode, false);
        _setLS(cacheKey, data);
        if (typeof renderMatches === 'function') renderMatches(data.matches);
        showStatus(data.last_update, buildStatusFlags(liveMeta, isFull));
    } else if (!cached?.matches?.length) {
        _showLoadError();
    }
}

setInterval(() => {
    if (document.visibilityState === 'visible') loadData();
}, AUTO_REFRESH_MS);

window.loadData = loadData;
