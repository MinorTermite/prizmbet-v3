/**
 * PrizmBet v2 - Bet Slip Module
 */
import { showToast } from './notifications.js';

export let currentBet = null;

export function setBet(data) {
    currentBet = data;
}

export function closeBetSlip() {
    const slip = document.getElementById('betSlip');
    if (slip) slip.classList.remove('show');
}

export function openBetSlip(betData, betType, coef) {
    const slip = document.getElementById('betSlip');
    if (!slip) return;
    
    currentBet = betData;
    
    document.getElementById('bsMatch').textContent = betData.teams;
    document.getElementById('bsMeta').textContent = `${betData.league} • #${betData.id}`;
    document.getElementById('bsOutcome').textContent = betType;
    document.getElementById('bsCoef').textContent = coef;
    
    slip.classList.add('show');
    calcPayout();
    if (navigator.vibrate) navigator.vibrate(30);
}

export function calcPayout() {
    const input = document.getElementById('bsInput');
    const coef = document.getElementById('bsCoef');
    const payout = document.getElementById('bsPayout');
    if (!input || !coef || !payout) return;
    
    const amount = parseFloat(input.value) || 0;
    const c = parseFloat(coef.textContent) || 0;
    payout.textContent = (amount * c).toFixed(2);
}

function _copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        return navigator.clipboard.writeText(text).catch(() => {
            _copyFallback(text);
        });
    }
    _copyFallback(text);
    return Promise.resolve();
}

function _copyFallback(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); } catch (_) {}
    document.body.removeChild(ta);
}

/**
 * Сокращает строку до max символов с «…» на конце.
 */
function _trunc(str, max) {
    return str && str.length > max ? str.slice(0, max - 1) + '…' : (str || '');
}

/**
 * Конвертирует "7 мар 10:30" → "07.03 10:30" (чистый ASCII, короче на ~3 байта).
 */
const _MONTHS = { 'янв':'01','фев':'02','мар':'03','апр':'04','май':'05','июн':'06',
                  'июл':'07','авг':'08','сен':'09','окт':'10','ноя':'11','дек':'12' };
function _compactDate(dt) {
    if (!dt) return '';
    const m = dt.match(/(\d{1,2})\s+([а-я]{3})\s+(\d{2}:\d{2})/i);
    if (!m) return dt.replace(/\s+/g, ' ').trim();
    const d = m[1].padStart(2,'0');
    const mo = _MONTHS[m[2].toLowerCase()] || '??';
    return `${d}.${mo} ${m[3]}`;
}

export function copyBetSlipData() {
    if (!currentBet) return;
    const amtInput = document.getElementById('bsInput');
    const amt = amtInput ? amtInput.value.trim() : '0';

    // Сокращаем названия команд до 20 символов каждое,
    // чтобы укложиться в лимит PRIZM-сети (~160 байт для зашифр. сообщения).
    const parts = (currentBet.teams || '').split(' vs ');
    const shortTeams = parts.length === 2
        ? `${_trunc(parts[0], 20)} vs ${_trunc(parts[1], 20)}`
        : _trunc(currentBet.teams, 40);

    const amtPart = amt && amt !== '0' ? `|${amt}PZM` : '';
    const dt = _compactDate(currentBet.datetime);
    const id  = currentBet.id || '';

    // Итоговый формат ≤ 160 байт:
    // "Erzurum BB vs Manisa B…, П1@1.49|1500PZM 07.03 10:30 #leon_123"
    const msg = `${shortTeams}, ${currentBet.betType}@${currentBet.coef}${amtPart ? ' ' + amtPart : ''} ${dt} #${id}`;

    // Show feedback on button, then close
    const btn = document.querySelector('#betSlip .bet-action-btn');
    if (btn) {
        const orig = btn.innerHTML;
        btn.innerHTML = '✅ Скопировано!';
        btn.disabled = true;
        setTimeout(() => { btn.innerHTML = orig; btn.disabled = false; }, 1200);
    }

    _copyText(msg).then(() => {
        showToast('✅ Данные скопированы!');
        setTimeout(() => {
            closeBetSlip();
            // Notify app for history saving
            window.dispatchEvent(new CustomEvent('betPlaced', {
                detail: { ...currentBet, amount: amt, timestamp: Date.now() }
            }));
        }, 900);
    });
}

export function toggleMyBets() {
    const modal = document.getElementById('myBetsModal');
    if (modal) modal.classList.toggle('show');
}

export async function checkMyBets() {
    const val = document.getElementById('walletInput')?.value.trim();
    const container = document.getElementById('betsListContainer');
    if (!val || !container) return;
    
    container.innerHTML = '<div style="text-align:center; color: var(--accent);"><span class="loading"></span> Загрузка...</div>';
    
    try {
        const r = await fetch('bets.json?t=' + Date.now());
        const data = await r.json();
        const bets = Array.isArray(data) ? data : (data.bets || []);
        
        const myBets = bets.filter(b => 
            (b.sender && b.sender.toUpperCase() === val.toUpperCase()) || 
            (b.tg_id && b.tg_id === val)
        );

        if (myBets.length === 0) {
            container.innerHTML = '<div style="text-align:center; color: var(--text-secondary); margin-top:20px;">Ставки не найдены 🥺</div>';
            return;
        }

        let html = '';
        [...myBets].reverse().forEach(b => {
            const statusClass = b.status === 'win' ? 'bet-status-win' : (b.status === 'loss' ? 'bet-status-loss' : 'bet-status-pending');
            const statusIcon = b.status === 'win' ? '✅ Выигрыш' : (b.status === 'loss' ? '❌ Проигрыш' : '⏳ В игре');
            
            html += `
                <div class="bet-item ${statusClass}">
                    <div style="display:flex; justify-content:space-between; margin-bottom: 6px;">
                        <strong style="color:#fff;">${b.team1} vs ${b.team2}</strong>
                        <span style="font-size:0.8rem; font-weight:600;">${statusIcon}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.6;">
                        Исход: <strong style="color:var(--accent-bright);">${b.bet_type}</strong> @ ${b.coef}<br>
                        Ставка: <strong style="color:#fff;">${b.amount} PRIZM</strong><br>
                        Выплата: <strong style="color: ${b.status === 'win' ? 'var(--green-bright)' : '#fff'};">${b.payout} PRIZM</strong><br>
                        <em>${b.time || ''}</em>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        container.innerHTML = '<div style="text-align:center; color: var(--red); margin-top:20px;">Ошибка загрузки базы ставок.</div>';
    }
}

export function copyWallet(btn) {
    const address = "PRIZM-4N7T-L2A7-RQZA-5BETW";
    _copyText(address).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = "✅ Скопировано!";
        setTimeout(() => btn.innerHTML = originalText, 2000);
    });
}
