/**
 * PrizmBet v3 - Notifications Module
 */
import { getFavDetails, saveFavDetails } from './storage.js';
import { t } from './i18n.js';

export function updateNotifBell() {
    const btn = document.getElementById('notifBtn');
    const mobileBtn = document.getElementById('mobileNotifBtn');
    [btn, mobileBtn].forEach((node) => {
        if (!node) return;
        if (Notification.permission === 'granted') {
            node.textContent = '??';
            node.style.opacity = '1';
        } else {
            node.textContent = '??';
            node.style.opacity = '0.7';
        }
    });
}

export async function requestNotificationPermission() {
    if (!('Notification' in window)) return false;
    if (Notification.permission === 'granted') return true;
    const permission = await Notification.requestPermission();
    return permission === 'granted';
}

export function playNotificationSound() {
    try {
        const audio = new Audio('https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3');
        audio.play();
    } catch (error) {
        console.error('Sound play failed', error);
    }
}

export function showNotification(title, body) {
    if (Notification.permission === 'granted') {
        new Notification(title, { body, icon: '/prizmbet-logo.webp' });
        playNotificationSound();
    }
}

export function checkFinishedFavorites(allMatches) {
    const details = getFavDetails();
    const favIds = Object.keys(details);
    if (favIds.length === 0) return;

    allMatches.forEach((match) => {
        if (favIds.includes(match.id) && match.score) {
            showNotification(
                t('common.matchFinishedTitle'),
                `${match.home_team || match.team1 || '?'} ${match.score} ${match.away_team || match.team2 || '?'}`
            );
            delete details[match.id];
            saveFavDetails(details);
        }
    });
}

export function showToast(msg) {
    const tLabel = document.getElementById('betToast');
    const brand = document.querySelector('.bet-toast-label');
    const message = document.getElementById('betToastMessage');
    if (brand) brand.textContent = t('toast.brand');
    if (tLabel && message) {
        message.textContent = msg;
        tLabel.classList.add('show');
        setTimeout(() => tLabel.classList.remove('show'), 3500);
    }
}
