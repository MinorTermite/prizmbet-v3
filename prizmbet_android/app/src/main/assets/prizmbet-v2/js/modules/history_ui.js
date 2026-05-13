/**
 * PrizmBet v2 - History UI Module
 */
import { getHistory } from './storage.js';
import { escapeHtml } from './utils.js';

export function openHistory() {
    const modal = document.getElementById('historyModal');
    const list = document.getElementById('historyList');
    if (!modal || !list) return;

    const history = getHistory();
    if (!history.length) {
        list.innerHTML = '<div style="text-align:center; padding: 30px 10px; color: var(--text-tertiary);">Вы еще не делали ставок.</div>';
    } else {
        list.innerHTML = history.map(h => {
            const dt = new Date(h.timestamp).toLocaleString('ru-RU', {
                day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit'
            });
            const payout = parseFloat(h.amount) * parseFloat(h.coef);
            const payoutText = payout > 0 ? `+${payout.toFixed(2)} PZM` : '—';
            return `
                <div class="history-item">
                    <div class="history-item-header">
                        <span>🕒 ${dt}</span>
                        <span style="color: #fff;">${h.amount} PZM</span>
                    </div>
                    <div class="history-item-match">${escapeHtml(h.teams)}</div>
                    <div class="history-item-details">
                        <span class="history-item-bet">${escapeHtml(h.betType)} @ ${escapeHtml(h.coef)}</span>
                        <span class="history-item-payout">${payoutText}</span>
                    </div>
                </div>
            `;
        }).join('');
    }
    modal.classList.add('show');
}

export function closeHistory() {
    const modal = document.getElementById('historyModal');
    if (modal) modal.classList.remove('show');
}

export function clearHistory() {
    if (confirm('Вы уверены, что хотите удалить локальную историю ставок?')) {
        localStorage.removeItem('prizmbet_history'); // Use literal or export constant
        openHistory();
    }
}
