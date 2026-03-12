/**
 * PrizmBet v3 - Utils Module
 */
import { formatDate, formatTime, getLanguage, t } from './i18n.js';

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

const RU_MONTHS = {
    '???': 0,
    '???': 1,
    '???': 2,
    '???': 3,
    '???': 4,
    '???': 5,
    '???': 6,
    '???': 7,
    '???': 8,
    '???': 9,
    '???': 10,
    '???': 11,
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
    if (!Number.isFinite(start) || start <= 0) return null;
    return Math.floor((start - Date.now()) / 60000);
}

export function isMatchLive(match) {
    if (match?.is_live === true) return true;
    const start = parseMatchDateTime(match);
    if (!Number.isFinite(start.getTime()) || start.getTime() <= 0) return false;
    const diffHours = (Date.now() - start.getTime()) / (1000 * 60 * 60);
    return diffHours >= 0 && diffHours < 2;
}

export function isMatchImminent(match, windowMinutes = 15) {
    if (isMatchLive(match)) return false;
    const minutes = getMinutesToStart(match);
    return minutes !== null && minutes > 0 && minutes <= windowMinutes;
}

export function getCountdownText(match) {
    if (isMatchLive(match)) return t('status.live');

    const start = parseMatchDateTime(match);
    if (!Number.isFinite(start.getTime()) || start.getTime() <= 0) return '';

    const diff = start.getTime() - Date.now();
    if (diff <= 0) return t('status.finished');

    const minutes = Math.floor(diff / 60000);
    if (minutes < 60) return getLanguage() === 'en' ? `${minutes} min` : `${minutes} ???`;

    const hours = Math.floor(minutes / 60);
    if (hours < 24) return getLanguage() === 'en' ? `${hours} h` : `${hours} ?`;

    return getLanguage() === 'en' ? `${Math.floor(hours / 24)} d` : `${Math.floor(hours / 24)} ?`;
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

export function formatMatchDate(match) {
    if (match.date) return match.date;
    if (!match.match_time) return t('common.todayLabel');
    return formatDate(match.match_time, { day: 'numeric', month: 'short' });
}

export function formatMatchTime(match) {
    if (match.time) return match.time;
    if (!match.match_time) return '';
    return formatTime(match.match_time, { hour: '2-digit', minute: '2-digit' });
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
        if (showToast) showToast(t('common.shareMatch'));
        const element = document.getElementById(`match-${id}`);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
            element.classList.add('highlight-pulse');
            setTimeout(() => element.classList.remove('highlight-pulse'), 1500);
        }
    });
}
