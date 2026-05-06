/**
 * PrizmBet v3 — Gamification Cabinet (v2)
 *
 * Enhances the existing #historyModal with:
 *   - Level character + progress bar
 *   - 5 tabs: Статистика | Задания | Бонусы | Рулетка | Розыгрыш
 *
 * Dependencies: i18n, utils, storage, bet_slip (getApiBase), notifications
 */
import { formatNumber, getLanguage } from './i18n.js';
import { escapeHtml } from './utils.js';
import { getWalletAddress } from './storage.js';
import { getApiBase } from './bet_slip.js';
import { showToast } from './notifications.js';

// ── State ──────────────────────────────────────────────────────────────────────

let _activeTab  = 'stats';
let _profile    = null;
let _activeRaffle = null;
let _betData    = null;   // passed in from history_ui.js
let _spinning   = false;
let _enteringRaffle = false;
let _initialized = false;

// ── Level character emoji fallback (until SVG assets are ready) ───────────────

const LEVEL_EMOJI = ['🌱','🎯','⚡','🔥','🏆','🎖️','🌟','💫','🚀','👑','🏅'];

// ── i18n strings ──────────────────────────────────────────────────────────────

function isEn() { return getLanguage() === 'en'; }

const S = {
    tabs: {
        stats:    () => isEn() ? 'Stats'     : 'Статистика',
        quests:   () => isEn() ? 'Quests'    : 'Задания',
        bonuses:  () => isEn() ? 'Bonuses'   : 'Бонусы',
        roulette: () => isEn() ? 'Roulette'  : 'Рулетка',
        raffle:   () => isEn() ? 'Raffle'    : 'Розыгрыш',
    },
    level:       () => isEn() ? 'Level'              : 'Уровень',
    spins:       () => isEn() ? 'spins'              : 'прокрутов',
    tokens:      () => isEn() ? 'raffle tokens'      : 'жетонов розыгрыша',
    nextLevel:   () => isEn() ? 'to next level'      : 'до следующего уровня',
    maxLevel:    () => isEn() ? 'Maximum level!'     : 'Максимальный уровень!',
    noQuests:    () => isEn() ? 'No quests yet.'     : 'Заданий пока нет.',
    noBonuses:   () => isEn() ? 'No active bonuses.' : 'Активных бонусов нет.',
    spinBtn:     () => isEn() ? 'Spin'               : 'Крутить',
    spinning:    () => isEn() ? 'Spinning…'          : 'Крутим…',
    noSpins:     () => isEn() ? 'Not enough spins'   : 'Недостаточно прокрутов',
    noRaffle:    () => isEn() ? 'No active raffle.'   : 'Активного розыгрыша нет.',
    enterRaffle: () => isEn() ? 'Enter raffle'        : 'Участвовать',
    entering:    () => isEn() ? 'Submitting…'         : 'Отправляем…',
    answerAll:   () => isEn() ? 'Answer all questions first.' : 'Сначала ответьте на все вопросы.',
    raffleOk:    () => isEn() ? 'Raffle entry accepted.'      : 'Участие в розыгрыше принято.',
    raffleErr:   () => isEn() ? 'Raffle entry failed.'        : 'Не удалось войти в розыгрыш.',
    locked:      () => isEn() ? 'Locked until wallet verification is enabled.' : 'Требуется подтверждение кошелька. Рулетка и розыгрыш временно отключены.',
    prize:       () => isEn() ? 'Prize'              : 'Приз',
    nothing:     () => isEn() ? 'No prize — try again!' : 'Пусто — попробуй ещё!',
    questDone:   () => isEn() ? '✓ Completed'        : '✓ Выполнено',
    active:      () => isEn() ? 'Active'             : 'Активен',
    queued:      () => isEn() ? 'Queued'             : 'В очереди',
    expires:     () => isEn() ? 'Expires'            : 'До',
    cabinetErr:  () => isEn() ? 'Failed to load gamification data.' : 'Не удалось загрузить данные геймификации.',
    rouletteErr: () => isEn() ? 'Roulette error — try again.'       : 'Ошибка рулетки — попробуй ещё раз.',
};

// ── Prize labels ──────────────────────────────────────────────────────────────

const PRIZE_LABELS = {
    nothing:          () => isEn() ? '😢 No prize'                   : '😢 Пусто',
    spins_15:         () => isEn() ? '🎰 +15 Spins'                  : '🎰 +15 прокрутов',
    cashback_20:      () => isEn() ? '💸 20% Cashback (30 days)'     : '💸 Кэшбэк 20% (30 дней)',
    win_boost_50:     () => isEn() ? '⚡ Win Boost +50% (7 days)'    : '⚡ Буст победы +50% (7 дней)',
    temp_millionaire: () => isEn() ? '👑 Temp Millionaire! (7 days)' : '👑 Миллионер на время! (7 дней)',
    raffle_token:     () => isEn() ? '🎫 Raffle Token'               : '🎫 Жетон розыгрыша',
};

// ── Init ──────────────────────────────────────────────────────────────────────

export function initCabinetV2() {
    if (_initialized) return;
    _initialized = true;

    // Listen for language change
    window.addEventListener('one-prizmbet:language-changed', () => {
        const root = document.getElementById('cabinetV2Root');
        if (root && _profile) _renderAll();
    });
}

// ── Public: render gamification panel ─────────────────────────────────────────

/**
 * Main entry point. Call from history_ui.js after cabinet opens.
 * @param {string} wallet  - PRIZM wallet address
 * @param {object} betData - data from getCabinetData() (bet history, stats, rank)
 */
export async function renderGamification(wallet, betData) {
    initCabinetV2();
    _betData = betData || null;
    _profile = null;
    _activeRaffle = null;

    _ensureRoot();

    if (!wallet) {
        _setRootHtml('<div class="cabinet-empty">Введите кошелёк для загрузки профиля.</div>');
        return;
    }

    const apiBase = getApiBase();
    if (!apiBase) {
        // API not connected — silently skip gamification panel
        _setRootHtml('');
        return;
    }

    _setRootHtml(_loadingHtml());

    try {
        const [resp, raffleResp] = await Promise.all([
            fetch(`${apiBase}/api/player/${encodeURIComponent(wallet)}`, { mode: 'cors' }),
            fetch(`${apiBase}/api/raffles/active`, { mode: 'cors' }).catch(() => null),
        ]);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const json = await resp.json();
        _profile = json;
        if (raffleResp && raffleResp.ok) {
            const raffleJson = await raffleResp.json().catch(() => ({}));
            _activeRaffle = raffleJson.raffle || null;
        }
        _renderAll();
    } catch (_) {
        _setRootHtml(`<div class="cabinet-empty">${escapeHtml(S.cabinetErr())}</div>`);
    }
}

// ── Root container ─────────────────────────────────────────────────────────────

function _ensureRoot() {
    if (document.getElementById('cabinetV2Root')) return;
    const modal = document.getElementById('historyModal');
    if (!modal) return;

    // Insert v2 root BEFORE the existing #cabinetStats
    const statsEl = document.getElementById('cabinetStats');
    const root = document.createElement('div');
    root.id = 'cabinetV2Root';

    if (statsEl) {
        modal.insertBefore(root, statsEl);
        // Hide legacy rank box — v2 replaces it
        const rankBox = document.querySelector('.cabinet-rank-box');
        if (rankBox) rankBox.style.display = 'none';
    } else {
        modal.appendChild(root);
    }
}

function _setRootHtml(html) {
    const root = document.getElementById('cabinetV2Root');
    if (root) root.innerHTML = html;
}

// ── Render all ─────────────────────────────────────────────────────────────────

function _renderAll() {
    if (!_profile) return;
    if (!_isTabAvailable(_activeTab)) _activeTab = 'stats';

    const profile    = _profile.profile || {};
    const progress   = profile.level_progress || {};
    const level      = progress.current_level || 1;
    const levelName  = progress.level_name || 'НАБЛЮДАТЕЛЬ';
    const wonPrizm   = progress.total_won_prizm || 0;
    const nextTarget = progress.next_level_turnover || 0;
    const remaining  = progress.remaining_prizm || 0;
    const pct        = progress.progress_percent || 0;
    const spins      = profile.roulette_spins || 0;
    const tokens     = profile.raffle_tokens  || 0;
    const emoji      = LEVEL_EMOJI[Math.min(level - 1, LEVEL_EMOJI.length - 1)];

    const html = `
        <div class="cv2-panel">

            <!-- Character + level -->
            <div class="cv2-hero">
                <div class="cv2-character">
                    <img
                        src="player-level-${level}.svg"
                        alt="${escapeHtml(levelName)}"
                        class="cv2-character-img"
                        onerror="this.style.display='none';this.nextElementSibling.style.display='block'"
                    />
                    <span class="cv2-character-emoji" style="display:none">${emoji}</span>
                </div>
                <div class="cv2-hero-info">
                    <div class="cv2-level-badge">${escapeHtml(S.level())} ${level}</div>
                    <div class="cv2-level-name">${escapeHtml(levelName)}</div>
                    <div class="cv2-counters">
                        <span class="cv2-counter">🎰 ${formatNumber(spins)} ${escapeHtml(S.spins())}</span>
                        <span class="cv2-counter">🎫 ${formatNumber(tokens)} ${escapeHtml(S.tokens())}</span>
                    </div>
                </div>
            </div>

            <!-- Progress bar -->
            <div class="cv2-progress-wrap">
                ${progress.next_level
                    ? `<div class="cv2-progress-label">
                           <span>${formatNumber(wonPrizm, {maximumFractionDigits: 0})} PRIZM</span>
                           <span>${formatNumber(nextTarget, {maximumFractionDigits: 0})} PRIZM</span>
                       </div>
                       <div class="cv2-progress-bar">
                           <div class="cv2-progress-fill" style="width:${pct}%"></div>
                       </div>
                       <div class="cv2-progress-hint">
                           ${escapeHtml(formatNumber(remaining, {maximumFractionDigits: 0}))} PRIZM ${escapeHtml(S.nextLevel())}
                       </div>`
                    : `<div class="cv2-progress-hint cv2-max-level">${escapeHtml(S.maxLevel())}</div>`
                }
            </div>

            <!-- Tabs -->
            <div class="cv2-tabs" id="cv2Tabs">
                ${_renderTabHeaders()}
            </div>

            <!-- Tab content -->
            <div class="cv2-tab-content" id="cv2TabContent">
                ${_renderActiveTab()}
            </div>
        </div>
    `;

    _setRootHtml(html);
    _bindTabEvents();
    _bindRouletteEvents();
    _bindRaffleEvents();
}

// ── Tabs ───────────────────────────────────────────────────────────────────────

function _renderTabHeaders() {
    const tabs = [
        { id: 'stats',    label: S.tabs.stats()    },
        { id: 'quests',   label: S.tabs.quests()   },
        { id: 'bonuses',  label: S.tabs.bonuses()  },
        { id: 'roulette', label: S.tabs.roulette() },
        { id: 'raffle',   label: S.tabs.raffle()   },
    ].filter(tab => _isTabAvailable(tab.id));
    return tabs.map(tab => `
        <button
            class="cv2-tab-btn ${_activeTab === tab.id ? 'is-active' : ''}"
            data-tab="${tab.id}"
            type="button"
        >${escapeHtml(tab.label)}</button>
    `).join('');
}

function _renderActiveTab() {
    if (!_isTabAvailable(_activeTab)) return _renderStatsTab();
    switch (_activeTab) {
        case 'stats':    return _renderStatsTab();
        case 'quests':   return _renderQuestsTab();
        case 'bonuses':  return _renderBonusesTab();
        case 'roulette': return _renderRouletteTab();
        case 'raffle':   return _renderRaffleTab();
        default:         return '';
    }
}

function _bindTabEvents() {
    const tabs = document.getElementById('cv2Tabs');
    if (!tabs) return;
    tabs.querySelectorAll('.cv2-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (!_isTabAvailable(btn.dataset.tab)) return;
            _activeTab = btn.dataset.tab;
            // Re-render tabs header (active state) + content
            const header = document.getElementById('cv2Tabs');
            const content = document.getElementById('cv2TabContent');
            if (header)  header.innerHTML  = _renderTabHeaders();
            if (content) content.innerHTML = _renderActiveTab();
            _bindTabEvents();
            _bindRouletteEvents();
            _bindRaffleEvents();
        });
    });
}

// ── Stats tab ──────────────────────────────────────────────────────────────────

function _renderStatsTab() {
    // Re-use existing bet stats rendered by history_ui.js into #cabinetStats
    // We show a lightweight summary here + delegate to the legacy #cabinetStats + #historyList

    // Show legacy containers again
    const legacy = ['cabinetStats', 'historyList'];
    legacy.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = '';
    });

    return `<div class="cv2-stats-note">
        <span style="opacity:.55;font-size:.82rem">
            ${isEn() ? 'Bet history below ↓' : 'История ставок ниже ↓'}
        </span>
    </div>`;
}

// ── Quests tab ─────────────────────────────────────────────────────────────────

function _renderQuestsTab() {
    _hideLegacy();
    const quests = (_profile?.quests || []);
    if (!quests.length) {
        return `<div class="cv2-empty">${escapeHtml(S.noQuests())}</div>`;
    }

    const currentLevel = _profile?.profile?.level_progress?.current_level || 1;

    // Group by level
    const grouped = {};
    quests.forEach(q => {
        const lvl = q.level_unlocked || 1;
        if (!grouped[lvl]) grouped[lvl] = [];
        grouped[lvl].push(q);
    });

    return Object.entries(grouped).map(([lvl, qs]) => `
        <div class="cv2-quest-group">
            <div class="cv2-quest-group-title">
                ${isEn() ? `Level ${lvl}` : `Уровень ${lvl}`}
                ${Number(lvl) > currentLevel ? `<span class="cv2-preview-badge">${isEn() ? 'preview' : 'превью'}</span>` : ''}
            </div>
            ${qs.map(q => _renderQuestCard(q)).join('')}
        </div>
    `).join('');
}

function _renderQuestCard(q) {
    const progress  = Math.min(Number(q.progress || 0), Number(q.target || 1));
    const target    = Number(q.target || 1);
    const pct       = Math.round(Math.min(100, (progress / target) * 100));
    const done      = Boolean(q.completed);
    const title     = q.title || q.quest_id || '';
    const desc      = q.description || '';
    const rewards   = Array.isArray(q.rewards) ? q.rewards : [];
    const times     = q.times_required > 1
        ? ` (${q.times_completed || 0}/${q.times_required})`
        : '';

    return `
        <div class="cv2-quest-card ${done ? 'is-done' : ''}">
            <div class="cv2-quest-header">
                <span class="cv2-quest-desc">${escapeHtml(title)}${escapeHtml(times)}</span>
                ${done ? `<span class="cv2-quest-done">${escapeHtml(S.questDone())}</span>` : ''}
            </div>
            ${desc ? `<div class="cv2-quest-meta">${escapeHtml(desc)}</div>` : ''}
            ${rewards.length ? `<div class="cv2-quest-rewards">${rewards.map(_renderQuestReward).join('')}</div>` : ''}
            ${!done ? `
                <div class="cv2-quest-bar-wrap">
                    <div class="cv2-quest-bar">
                        <div class="cv2-quest-fill" style="width:${pct}%"></div>
                    </div>
                    <span class="cv2-quest-pct">${pct}%</span>
                </div>
                <div class="cv2-quest-numbers">
                    ${formatNumber(progress, {maximumFractionDigits: 0})}
                    /
                    ${formatNumber(target, {maximumFractionDigits: 0})}
                </div>
            ` : ''}
        </div>
    `;
}

function _renderQuestReward(reward) {
    const type = reward?.type || '';
    if (type === 'roulette_spins') {
        return `<span class="cv2-quest-reward">+${formatNumber(Number(reward.value || 0))} ${escapeHtml(S.spins())}</span>`;
    }
    if (type === 'raffle_token') {
        return `<span class="cv2-quest-reward">+${formatNumber(Number(reward.value || 1))} ${escapeHtml(S.tokens())}</span>`;
    }
    if (type === 'badge') {
        return `<span class="cv2-quest-reward">${isEn() ? 'Badge' : 'Значок'}: ${escapeHtml(reward.badge || '')}</span>`;
    }
    if (type === 'bonus') {
        return `<span class="cv2-quest-reward">${escapeHtml(_bonusTypeLabel(reward.bonus_type, reward.bonus_key, reward.value))}</span>`;
    }
    return '';
}

// ── Bonuses tab ────────────────────────────────────────────────────────────────

function _renderBonusesTab() {
    _hideLegacy();
    const bonuses = (_profile?.bonuses || []);
    if (!bonuses.length) {
        return `<div class="cv2-empty">${escapeHtml(S.noBonuses())}</div>`;
    }

    return bonuses.map(b => _renderBonusCard(b)).join('');
}

function _renderBonusCard(b) {
    const isActive = Boolean(b.activated);
    const typeLabel = _bonusTypeLabel(b.bonus_type, b.bonus_key, b.value);
    const expiry    = b.expires_at ? new Date(b.expires_at).toLocaleDateString(
        isEn() ? 'en-GB' : 'ru-RU', { day: '2-digit', month: '2-digit', year: '2-digit' }
    ) : '—';

    return `
        <div class="cv2-bonus-card ${isActive ? 'is-active' : 'is-queued'}">
            <div class="cv2-bonus-header">
                <span class="cv2-bonus-label">${escapeHtml(typeLabel)}</span>
                <span class="cv2-bonus-status ${isActive ? 'cv2-status-active' : 'cv2-status-queued'}">
                    ${isActive ? escapeHtml(S.active()) : escapeHtml(S.queued())}
                </span>
            </div>
            <div class="cv2-bonus-meta">
                ${escapeHtml(S.expires())}: ${escapeHtml(expiry)}
                ${b.burn_on_level_up ? ` · ${isEn() ? 'burns on level-up' : 'сгорит при повышении'}` : ''}
            </div>
        </div>
    `;
}

function _bonusTypeLabel(type, key, value) {
    const pct = _formatBonusPercent(value);
    if (key === 'cashback_20')      return `💸 ${isEn() ? `Cashback ${pct}%` : `Кэшбэк ${pct}%`}`;
    if (key === 'win_boost_50')     return `⚡ ${isEn() ? `Win Boost +${pct}%` : `Буст победы +${pct}%`}`;
    if (key === 'temp_millionaire') return `👑 ${isEn() ? 'Temp Millionaire' : 'Миллионер на время'}`;
    if (type === 'cashback')        return `💸 ${isEn() ? `Cashback ${pct}%` : `Кэшбэк ${pct}%`}`;
    if (type === 'pct_win')         return `⚡ ${isEn() ? `Win Boost +${pct}%` : `Буст победы +${pct}%`}`;
    if (type === 'roulette_spins')  return `🎰 ${isEn() ? `+${value} Spins` : `+${value} прокрутов`}`;
    if (type === 'raffle_token')    return `🎫 ${isEn() ? 'Raffle Token' : 'Жетон розыгрыша'}`;
    if (type === 'freespins')       return `🆓 ${isEn() ? 'Free Spins' : 'Бесплатные прокруты'}`;
    return escapeHtml(key || type || '?');
}

function _formatBonusPercent(value) {
    const percent = Number(value || 0) * 100;
    if (percent > 0 && percent < 1) {
        return percent.toFixed(1).replace(/\.0$/, '');
    }
    return String(Math.round(percent));
}

// ── Roulette tab ───────────────────────────────────────────────────────────────

function _renderRouletteTab() {
    _hideLegacy();
    if (!_gamificationMutationsEnabled()) {
        return _lockedMutationHtml(S.tabs.roulette());
    }
    const spins = Number(_profile?.profile?.roulette_spins || 0);

    return `
        <div class="cv2-roulette">
            <div class="cv2-roulette-counter">
                🎰 <strong>${formatNumber(spins)}</strong> ${escapeHtml(S.spins())}
            </div>

            <div class="cv2-roulette-controls">
                <label class="cv2-spin-label">
                    ${isEn() ? 'Spins to use' : 'Использовать прокрутов'}
                    <select class="cv2-spin-select" id="cv2SpinCount" ${spins < 1 ? 'disabled' : ''}>
                        ${[1,5,10,25,50].filter(n => n <= Math.max(spins, 1)).map(n =>
                            `<option value="${n}">${n}</option>`
                        ).join('')}
                    </select>
                </label>
                <button
                    class="btn btn-primary cv2-spin-btn"
                    id="cv2SpinBtn"
                    type="button"
                    ${spins < 1 ? 'disabled' : ''}
                >
                    ${spins < 1 ? escapeHtml(S.noSpins()) : escapeHtml(S.spinBtn())}
                </button>
            </div>

            <div class="cv2-roulette-results" id="cv2RouletteResults"></div>

            <div class="cv2-roulette-hint">
                ${isEn()
                    ? '1 spin = 1,500 PRIZM bet. Prizes are random — odds are in the rules.'
                    : '1 прокрут = 1 500 PRIZM ставки. Призы случайны — шансы указаны в правилах.'}
            </div>
        </div>
    `;
}

function _bindRouletteEvents() {
    const btn = document.getElementById('cv2SpinBtn');
    if (!btn) return;
    btn.addEventListener('click', _handleSpin);
}

async function _handleSpin() {
    if (!_gamificationMutationsEnabled()) {
        showToast(S.locked());
        return;
    }
    if (_spinning) return;

    const wallet = getWalletAddress();
    if (!wallet) return;

    const apiBase = getApiBase();
    if (!apiBase) return;

    const countEl = document.getElementById('cv2SpinCount');
    const spins   = parseInt(countEl?.value || '1', 10);

    const btn = document.getElementById('cv2SpinBtn');
    const resultsEl = document.getElementById('cv2RouletteResults');

    _spinning = true;
    if (btn) { btn.disabled = true; btn.textContent = S.spinning(); }
    if (resultsEl) resultsEl.innerHTML = '';

    try {
        const resp = await fetch(`${apiBase}/api/player/${encodeURIComponent(wallet)}/roulette`, {
            method: 'POST',
            mode:   'cors',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ spins }),
        });

        const json = await resp.json();

        if (!resp.ok) {
            showToast(json.error || S.rouletteErr());
            return;
        }

        // Refresh profile data
        try {
            const profileResp = await fetch(`${apiBase}/api/player/${encodeURIComponent(wallet)}`, { mode: 'cors' });
            if (profileResp.ok) {
                const updated = await profileResp.json();
                _profile = { ..._profile, ...updated };
            }
        } catch (_) {}

        // Show prizes
        const prizes = json.prizes || [];
        if (resultsEl) {
            resultsEl.innerHTML = prizes.map(p => {
                const labelFn = PRIZE_LABELS[p.prize_type];
                const label   = labelFn ? labelFn() : escapeHtml(p.prize_type);
                const isNothing = p.prize_type === 'nothing';
                return `
                    <div class="cv2-prize-row ${isNothing ? 'cv2-prize-nothing' : 'cv2-prize-win'}">
                        ${label}
                    </div>
                `;
            }).join('');
        }

        // Update spin counter in hero bar
        const newSpins = Number(_profile?.profile?.roulette_spins || 0);
        const counterEl = document.querySelector('.cv2-roulette-counter');
        if (counterEl) {
            counterEl.innerHTML = `🎰 <strong>${formatNumber(newSpins)}</strong> ${escapeHtml(S.spins())}`;
        }

        // Disable button if no spins left
        if (btn && newSpins < 1) {
            btn.textContent = S.noSpins();
        }

    } catch (_) {
        showToast(S.rouletteErr());
    } finally {
        _spinning = false;
        if (btn) {
            const spinsLeft = Number(_profile?.profile?.roulette_spins || 0);
            btn.disabled = spinsLeft < 1;
            btn.textContent = spinsLeft < 1 ? S.noSpins() : S.spinBtn();
        }
    }
}

// ── Raffle tab ────────────────────────────────────────────────────────────────

function _renderRaffleTab() {
    _hideLegacy();
    if (!_gamificationMutationsEnabled()) {
        return _lockedMutationHtml(S.tabs.raffle());
    }
    const raffle = _activeRaffle;
    const tokens = Number(_profile?.profile?.raffle_tokens || 0);
    if (!raffle) {
        return `<div class="cv2-empty">${escapeHtml(S.noRaffle())}</div>`;
    }

    const questions = Array.isArray(raffle.questions) ? raffle.questions : [];
    const disabled = tokens < 1;
    return `
        <form class="cv2-raffle" id="cv2RaffleForm">
            <div class="cv2-raffle-head">
                <div>
                    <div class="cv2-raffle-kicker">${isEn() ? 'Active raffle' : 'Активный розыгрыш'}</div>
                    <h3 class="cv2-raffle-title">${escapeHtml(raffle.title || (isEn() ? 'Raffle' : 'Розыгрыш'))}</h3>
                    <p class="cv2-raffle-copy">
                        ${isEn()
                            ? 'One entry spends one raffle token. Answers are submitted once.'
                            : 'Одно участие списывает один жетон. Ответы отправляются один раз.'}
                    </p>
                </div>
                <div class="cv2-raffle-token ${disabled ? 'is-empty' : ''}">
                    🎫 ${formatNumber(tokens)} ${escapeHtml(S.tokens())}
                </div>
            </div>
            <div class="cv2-raffle-window">
                ${_renderRaffleDate(raffle.starts_at)} — ${_renderRaffleDate(raffle.ends_at)}
            </div>
            <div class="cv2-raffle-questions">
                ${questions.map(_renderRaffleQuestion).join('')}
            </div>
            <div class="cv2-raffle-actions">
                <button class="btn btn-primary cv2-raffle-submit" id="cv2RaffleSubmit" type="submit" ${disabled || !questions.length ? 'disabled' : ''}>
                    ${disabled ? escapeHtml(isEn() ? 'Need raffle token' : 'Нужен жетон') : escapeHtml(S.enterRaffle())}
                </button>
                <div class="cv2-raffle-status" id="cv2RaffleStatus"></div>
            </div>
        </form>
    `;
}

function _renderRaffleQuestion(question, index) {
    const id = String(question?.id || index + 1);
    const text = String(question?.text || '');
    const options = Array.isArray(question?.options) ? question.options : [];
    return `
        <fieldset class="cv2-raffle-question" data-question-id="${_escapeAttr(id)}">
            <legend>${index + 1}. ${escapeHtml(text)}</legend>
            <div class="cv2-raffle-options">
                ${options.map((option, optionIndex) => {
                    const value = String(option || '');
                    const inputId = `cv2-raffle-${_safeDomId(id)}-${optionIndex}`;
                    return `
                        <label class="cv2-raffle-option" for="${_escapeAttr(inputId)}">
                            <input id="${_escapeAttr(inputId)}" name="raffle_${_escapeAttr(id)}" type="radio" value="${_escapeAttr(value)}">
                            <span>${escapeHtml(value)}</span>
                        </label>
                    `;
                }).join('')}
            </div>
        </fieldset>
    `;
}

function _bindRaffleEvents() {
    const form = document.getElementById('cv2RaffleForm');
    if (!form) return;
    form.addEventListener('submit', _handleRaffleSubmit);
}

async function _handleRaffleSubmit(event) {
    event.preventDefault();
    if (!_gamificationMutationsEnabled()) {
        showToast(S.locked());
        return;
    }
    if (_enteringRaffle) return;
    const raffle = _activeRaffle;
    const wallet = getWalletAddress();
    const apiBase = getApiBase();
    if (!raffle || !wallet || !apiBase) return;

    const questions = Array.isArray(raffle.questions) ? raffle.questions : [];
    const answers = questions.map((question, index) => {
        const id = String(question?.id || index + 1);
        const fieldset = document.querySelector(`[data-question-id="${_escapeSelectorAttr(id)}"]`);
        const checked = fieldset ? fieldset.querySelector('input:checked') : null;
        return checked ? { id, answer: checked.value } : null;
    });

    const statusEl = document.getElementById('cv2RaffleStatus');
    const submitBtn = document.getElementById('cv2RaffleSubmit');
    if (answers.some(answer => !answer)) {
        if (statusEl) statusEl.textContent = S.answerAll();
        return;
    }

    _enteringRaffle = true;
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = S.entering();
    }
    if (statusEl) statusEl.textContent = '';

    try {
        const resp = await fetch(`${apiBase}/api/raffles/${encodeURIComponent(raffle.id)}/enter`, {
            method: 'POST',
            mode: 'cors',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wallet, answers }),
        });
        const json = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            throw new Error(json.error || S.raffleErr());
        }
        showToast(S.raffleOk());
        if (statusEl) {
            statusEl.textContent = `${S.raffleOk()} ${isEn() ? 'Tokens left' : 'Жетонов осталось'}: ${formatNumber(json.tokens_remaining || 0)}.`;
        }
        await _refreshProfileAndRaffle(wallet, apiBase);
        _renderAll();
    } catch (error) {
        const message = String(error?.message || S.raffleErr());
        showToast(message);
        if (statusEl) statusEl.textContent = message;
    } finally {
        _enteringRaffle = false;
        if (submitBtn) {
            const tokens = Number(_profile?.profile?.raffle_tokens || 0);
            submitBtn.disabled = tokens < 1;
            submitBtn.textContent = tokens < 1 ? (isEn() ? 'Need raffle token' : 'Нужен жетон') : S.enterRaffle();
        }
    }
}

async function _refreshProfileAndRaffle(wallet, apiBase) {
    const [profileResp, raffleResp] = await Promise.all([
        fetch(`${apiBase}/api/player/${encodeURIComponent(wallet)}`, { mode: 'cors' }).catch(() => null),
        fetch(`${apiBase}/api/raffles/active`, { mode: 'cors' }).catch(() => null),
    ]);
    if (profileResp && profileResp.ok) {
        _profile = await profileResp.json().catch(() => _profile);
    }
    if (raffleResp && raffleResp.ok) {
        const raffleJson = await raffleResp.json().catch(() => ({}));
        _activeRaffle = raffleJson.raffle || null;
    }
}

function _renderRaffleDate(value) {
    if (!value) return isEn() ? 'open' : 'без срока';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleDateString(isEn() ? 'en-GB' : 'ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function _safeDomId(value) {
    return String(value || '').replace(/[^a-zA-Z0-9_-]/g, '_');
}

function _escapeAttr(value) {
    return escapeHtml(String(value || '')).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function _escapeSelectorAttr(value) {
    return String(value || '').replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function _gamificationMutationsEnabled() {
    return Boolean(_profile?.features?.gamification_public_mutations);
}

function _isTabAvailable(tabId) {
    if (tabId === 'roulette' || tabId === 'raffle') {
        return _gamificationMutationsEnabled();
    }
    return true;
}

function _lockedMutationHtml(title) {
    return `<div class="cv2-empty"><strong>${escapeHtml(title)}</strong><br>${escapeHtml(S.locked())}</div>`;
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function _hideLegacy() {
    ['cabinetStats', 'historyList'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'none';
    });
}

function _loadingHtml() {
    return `<div class="cabinet-empty">
        ${isEn() ? '⏳ Loading profile…' : '⏳ Загружаем профиль…'}
    </div>`;
}
