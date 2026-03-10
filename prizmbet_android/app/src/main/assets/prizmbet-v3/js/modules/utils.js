/**
 * PrizmBet v2 - Utils Module
 */

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

const _RU_MON = { 'янв':0,'фев':1,'мар':2,'апр':3,'май':4,'июн':5,'июл':6,'авг':7,'сен':8,'окт':9,'ноя':10,'дек':11 };

export function parseMatchDateTime(match) {
    // Priority 1: ISO match_time field
    if (match.match_time) {
        const d = new Date(match.match_time);
        if (!isNaN(d)) return d;
    }
    // Priority 2: date + time string fields (e.g. "6 мар" + "15:30")
    const dateStr = (match.date || '').trim();
    const timeStr = (match.time || '').trim();
    if (!dateStr) return new Date(0);

    const parts = dateStr.split(/\s+/);
    const day = parseInt(parts[0], 10);
    if (!isNaN(day) && parts[1]) {
        const mon = _RU_MON[parts[1].toLowerCase()];
        if (mon !== undefined) {
            const year = parts[2] ? parseInt(parts[2], 10) : new Date().getFullYear();
            const [h = 0, m = 0] = timeStr.includes(':') ? timeStr.split(':').map(Number) : [];
            return new Date(year, mon, day, h, m);
        }
    }
    // Priority 3: "06.03.2026" format
    const dot = dateStr.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
    if (dot) {
        const [h = 0, m = 0] = timeStr.includes(':') ? timeStr.split(':').map(Number) : [];
        return new Date(+dot[3], +dot[2] - 1, +dot[1], h, m);
    }
    return new Date(0);
}

export function isMatchLive(match) {
    const start = parseMatchDateTime(match);
    const now = new Date();
    const diffHours = (now - start) / (1000 * 60 * 60);
    return diffHours >= 0 && diffHours < 2;
}

export function getCountdownText(match) {
    const start = parseMatchDateTime(match);
    const now = new Date();
    const diff = start - now;
    if (diff <= 0) return isMatchLive(match) ? "LIVE" : "Завершен";
    
    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes} м`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} ч`;
    return `${Math.floor(hours / 24)} д`;
}

// Global UI helpers
export function initScrollProgress() {
    window.addEventListener('scroll', () => {
        const h = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const bar = document.getElementById('scrollProgress');
        if (h > 0 && bar) {
            bar.style.width = ((document.documentElement.scrollTop / h) * 100) + '%';
        }
    });
}

export function initTabsHint() {
    const tabs = document.getElementById('tabsRow');
    const wrap = document.getElementById('tabsWrap');
    if (!tabs || !wrap) return;

    tabs.addEventListener('scroll', () => {
        const atEnd = tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 8;
        wrap.classList.toggle('scrolled-end', atEnd);
    }, { passive: true });
}

export function shareMatch(id, showToast) {
    const url = `${window.location.origin}${window.location.pathname}#match-${id}`;
    const _fallback = () => {
        const ta = document.createElement('textarea');
        ta.value = url;
        ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
        document.body.appendChild(ta);
        ta.focus(); ta.select();
        try { document.execCommand('copy'); } catch (_) {}
        document.body.removeChild(ta);
    };
    const p = (navigator.clipboard && navigator.clipboard.writeText)
        ? navigator.clipboard.writeText(url).catch(_fallback)
        : Promise.resolve(_fallback());
    p.then(() => {
        if (showToast) showToast('Ссылка на матч скопирована!');
        const el = document.getElementById('match-' + id);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            el.classList.add('highlight-pulse');
            setTimeout(() => el.classList.remove('highlight-pulse'), 1500);
        }
    });
}
