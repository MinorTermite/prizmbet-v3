/**
 * PrizmBet v3 - Utils Module
 */

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

const RU_MONTHS = {
    'янв': 0,
    'фев': 1,
    'мар': 2,
    'апр': 3,
    'май': 4,
    'июн': 5,
    'июл': 6,
    'авг': 7,
    'сен': 8,
    'окт': 9,
    'ноя': 10,
    'дек': 11,
};

export function parseMatchDateTime(match) {
    if (match.match_time) {
        const date = new Date(match.match_time);
        if (!Number.isNaN(date.getTime())) return date;
    }

    const dateStr = String(match.date || '').trim();
    const timeStr = String(match.time || '').trim();
    if (!dateStr) return new Date(0);

    const parts = dateStr.split(/\s+/);
    const day = Number.parseInt(parts[0], 10);
    if (!Number.isNaN(day) && parts[1]) {
        const month = RU_MONTHS[String(parts[1]).toLowerCase()];
        if (month !== undefined) {
            const year = parts[2] ? Number.parseInt(parts[2], 10) : new Date().getFullYear();
            const [hours = 0, minutes = 0] = timeStr.includes(':') ? timeStr.split(':').map(Number) : [];
            return new Date(year, month, day, hours, minutes);
        }
    }

    const dotMatch = dateStr.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/);
    if (dotMatch) {
        const [hours = 0, minutes = 0] = timeStr.includes(':') ? timeStr.split(':').map(Number) : [];
        return new Date(Number(dotMatch[3]), Number(dotMatch[2]) - 1, Number(dotMatch[1]), hours, minutes);
    }

    return new Date(0);
}

export function getMinutesToStart(match) {
    const start = parseMatchDateTime(match).getTime();
    if (!start) return null;
    return Math.floor((start - Date.now()) / 60000);
}

export function isMatchLive(match) {
    const start = parseMatchDateTime(match);
    const diffHours = (Date.now() - start.getTime()) / (1000 * 60 * 60);
    return diffHours >= 0 && diffHours < 2;
}

export function isMatchImminent(match, windowMinutes = 15) {
    if (isMatchLive(match)) return false;
    const minutes = getMinutesToStart(match);
    return minutes !== null && minutes > 0 && minutes <= windowMinutes;
}

export function getCountdownText(match) {
    const start = parseMatchDateTime(match);
    const diff = start.getTime() - Date.now();
    if (diff <= 0) return isMatchLive(match) ? 'LIVE' : 'Завершён';

    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return `${minutes} м`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} ч`;
    return `${Math.floor(hours / 24)} д`;
}

export function initScrollProgress() {
    window.addEventListener('scroll', () => {
        const fullHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const bar = document.getElementById('scrollProgress');
        if (fullHeight > 0 && bar) {
            bar.style.width = `${(document.documentElement.scrollTop / fullHeight) * 100}%`;
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
    const fallbackCopy = () => {
        const area = document.createElement('textarea');
        area.value = url;
        area.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
        document.body.appendChild(area);
        area.focus();
        area.select();
        try { document.execCommand('copy'); } catch (_) {}
        document.body.removeChild(area);
    };

    const promise = (navigator.clipboard && navigator.clipboard.writeText)
        ? navigator.clipboard.writeText(url).catch(fallbackCopy)
        : Promise.resolve(fallbackCopy());

    promise.then(() => {
        if (showToast) showToast('Ссылка на матч скопирована.');
        const element = document.getElementById(`match-${id}`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            element.classList.add('highlight-pulse');
            setTimeout(() => element.classList.remove('highlight-pulse'), 1500);
        }
    });
}
