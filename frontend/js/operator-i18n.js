(function () {
  const KEY = 'prizmbet_lang_v1';
    const STATIC = {
    ru: {
      'page.title': 'PRIZMBET - Кабинет оператора',
      'hero.eyebrow': 'Кабинет оператора',
      'hero.title': 'Ставки, пользователи и аудит',
      'hero.copy': 'Панель работает на именных аккаунтах операторов. Действия по ставкам и выплатам привязаны к конкретной пользовательской сессии.',
      'hero.back': 'Вернуться на сайт',
      'access.apiBase': 'API base',
      'access.apiBasePlaceholder': 'https://your-backend.example',
      'access.connect': 'Подключить',
      'access.refresh': 'Обновить',
      'access.autoRefresh': 'Автообновление',
      'bootstrap.eyebrow': 'Первичная настройка',
      'bootstrap.title': 'Создать super admin',
      'bootstrap.copy': 'Этот шаг выполняется один раз для первичной настройки панели.',
      'bootstrap.email': 'Email администратора',
      'bootstrap.emailPlaceholder': 'admin@example.com',
      'bootstrap.login': 'Логин администратора',
      'bootstrap.loginPlaceholder': 'admin',
      'bootstrap.password': 'Пароль',
      'bootstrap.passwordPlaceholder': 'Минимум 8 символов',
      'bootstrap.key': 'Bootstrap key',
      'bootstrap.keyPlaceholder': 'ADMIN_VIEW_KEY из .env',
      'bootstrap.action': 'Создать admin-аккаунт',
      'login.eyebrow': 'Вход',
      'login.title': 'Войти как оператор',
      'login.copy': 'Используйте назначенный логин или email и свой пароль.',
      'login.identity': 'Логин или email',
      'login.identityPlaceholder': 'login или name@example.com',
      'login.password': 'Пароль',
      'login.passwordPlaceholder': 'Пароль',
      'login.action': 'Войти',
      'session.eyebrow': 'Сессия',
      'session.title': 'Текущий оператор',
      'session.user': 'Оператор',
      'session.expires': 'Сессия истекает',
      'session.logout': 'Выйти',
      'users.eyebrow': 'Управление пользователями',
      'users.title': 'Назначенные операторы',
      'users.copy': 'Только super admin может создавать и отключать операторские аккаунты.',
      'users.login': 'Логин',
      'users.loginPlaceholder': 'operator.login',
      'users.email': 'Email',
      'users.emailPlaceholder': 'optional@example.com',
      'users.password': 'Пароль',
      'users.passwordPlaceholder': 'Минимум 8 символов',
      'users.role': 'Роль',
      'users.action': 'Создать пользователя',
      'role.operator': 'Оператор',
      'role.finance': 'Финансы',
      'role.viewer': 'Наблюдатель',
      'feed.searchPlaceholder': 'Поиск по матчу, TX, кошельку, коду или лиге',
      'statusFilter.all': 'Все статусы',
      'status.accepted': 'Принята',
      'status.rejected': 'Отклонена',
      'status.won': 'Выиграла',
      'status.lost': 'Проиграла',
      'status.refund_pending': 'Возврат ожидается',
      'status.paid': 'Выплачена',
      'audit.eyebrow': 'Журнал аудита',
      'audit.title': 'Последние backend и operator события',
      'audit.copy': 'Здесь фиксируются принятые, отклонённые, рассчитанные и выплаченные ставки. При включённом webhook те же события могут зеркалироваться в Google Sheets.'
    },
    en: {
      'page.title': 'PRIZMBET - Operator Console',
      'hero.eyebrow': 'Operator Console',
      'hero.title': 'Bets, users and activity log',
      'hero.copy': 'This panel uses named operator accounts. Bet and payout actions stay tied to a specific user session.',
      'hero.back': 'Back to site',
      'access.apiBase': 'API base',
      'access.apiBasePlaceholder': 'https://your-backend.example',
      'access.connect': 'Connect',
      'access.refresh': 'Refresh',
      'access.autoRefresh': 'Auto refresh',
      'bootstrap.eyebrow': 'Initial setup',
      'bootstrap.title': 'Create admin',
      'bootstrap.copy': 'This step runs once for the initial panel setup.',
      'bootstrap.email': 'Administrator email',
      'bootstrap.emailPlaceholder': 'admin@example.com',
      'bootstrap.login': 'Administrator login',
      'bootstrap.loginPlaceholder': 'admin',
      'bootstrap.password': 'Password',
      'bootstrap.passwordPlaceholder': 'Minimum 8 characters',
      'bootstrap.key': 'Bootstrap key',
      'bootstrap.keyPlaceholder': 'ADMIN_VIEW_KEY from .env',
      'bootstrap.action': 'Create account',
      'login.eyebrow': 'Login',
      'login.title': 'Enter as operator',
      'login.copy': 'Use the assigned login or email and your password.',
      'login.identity': 'Login or email',
      'login.identityPlaceholder': 'login or name@example.com',
      'login.password': 'Password',
      'login.passwordPlaceholder': 'Password',
      'login.action': 'Log in',
      'session.eyebrow': 'Session',
      'session.title': 'Current operator',
      'session.user': 'Operator',
      'session.expires': 'Session expires',
      'session.logout': 'Log out',
      'users.eyebrow': 'User Management',
      'users.title': 'Assigned operators',
      'users.copy': 'Only admin can create or disable operator accounts.',
      'users.login': 'Login',
      'users.loginPlaceholder': 'operator.login',
      'users.email': 'Email',
      'users.emailPlaceholder': 'optional@example.com',
      'users.password': 'Password',
      'users.passwordPlaceholder': 'Minimum 8 characters',
      'users.role': 'Role',
      'users.action': 'Create user',
      'role.operator': 'Operator',
      'role.finance': 'Finance',
      'role.viewer': 'Viewer',
      'feed.searchPlaceholder': 'Search by match, TX, wallet, intent or league',
      'statusFilter.all': 'All statuses',
      'status.accepted': 'Accepted',
      'status.rejected': 'Rejected',
      'status.won': 'Won',
      'status.lost': 'Lost',
      'status.refund_pending': 'Refund pending',
      'status.paid': 'Paid',
      'audit.eyebrow': 'Audit Log',
      'audit.title': 'Recent backend and operator events',
      'audit.copy': 'Accepted, rejected, settled and paid events are listed here. If the webhook is enabled, the same events can be mirrored to Google Sheets.'
    }
  };

const EXACT = {
    ru: {
      'Set API base and connect.': 'РЈРєР°Р¶РёС‚Рµ API base Рё РїРѕРґРєР»СЋС‡РёС‚РµСЃСЊ.',
      'Set API base first.': 'РЎРЅР°С‡Р°Р»Р° СѓРєР°Р¶РёС‚Рµ API base.',
      'Connect to inspect the operator auth state.': 'РџРѕРґРєР»СЋС‡РёС‚РµСЃСЊ, С‡С‚РѕР±С‹ РїСЂРѕРІРµСЂРёС‚СЊ СЃРѕСЃС‚РѕСЏРЅРёРµ Р°РІС‚РѕСЂРёР·Р°С†РёРё РѕРїРµСЂР°С‚РѕСЂРѕРІ.',
      'Checking operator access...': 'РџСЂРѕРІРµСЂСЏСЋ РґРѕСЃС‚СѓРї РѕРїРµСЂР°С‚РѕСЂР°...',
      'Auth state is unknown.': 'РЎРѕСЃС‚РѕСЏРЅРёРµ Р°РІС‚РѕСЂРёР·Р°С†РёРё РЅРµРёР·РІРµСЃС‚РЅРѕ.',
      'Feed not loaded yet.': 'Р›РµРЅС‚Р° РµС‰С‘ РЅРµ Р·Р°РіСЂСѓР¶РµРЅР°.',
      'Audit log not loaded yet.': 'Р–СѓСЂРЅР°Р» Р°СѓРґРёС‚Р° РµС‰С‘ РЅРµ Р·Р°РіСЂСѓР¶РµРЅ.',
      'Failed to copy value to clipboard.': 'РќРµ СѓРґР°Р»РѕСЃСЊ СЃРєРѕРїРёСЂРѕРІР°С‚СЊ Р·РЅР°С‡РµРЅРёРµ РІ Р±СѓС„РµСЂ РѕР±РјРµРЅР°.',
      'Failed to read bootstrap state.': 'РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕС‡РёС‚Р°С‚СЊ СЃРѕСЃС‚РѕСЏРЅРёРµ bootstrap.',
      'Admin session is invalid.': 'РЎРµСЃСЃРёСЏ Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂР° РЅРµРґРµР№СЃС‚РІРёС‚РµР»СЊРЅР°.',
      'Administrator email, login, password and bootstrap key are required.': 'Нужны email администратора, логин, пароль и bootstrap key.',
      'Administrator account created. Session is active.': 'Аккаунт администратора создан. Сессия активна.',
      'Failed to bootstrap administrator account.': 'Не удалось создать аккаунт администратора.',
      'Login/email and password are required.': 'РќСѓР¶РЅС‹ Р»РѕРіРёРЅ РёР»Рё email Рё РїР°СЂРѕР»СЊ.',
      'Failed to log in.': 'РќРµ СѓРґР°Р»РѕСЃСЊ РІРѕР№С‚Рё.',
      'Only the super admin can create users.': 'РўРѕР»СЊРєРѕ super admin РјРѕР¶РµС‚ СЃРѕР·РґР°РІР°С‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»РµР№.',
      'Failed to create user.': 'РќРµ СѓРґР°Р»РѕСЃСЊ СЃРѕР·РґР°С‚СЊ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.',
      'Failed to update user state.': 'РќРµ СѓРґР°Р»РѕСЃСЊ РѕР±РЅРѕРІРёС‚СЊ СЃРѕСЃС‚РѕСЏРЅРёРµ РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ.',
      'Failed to load admin users.': 'РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ СЃРїРёСЃРѕРє Р°РґРјРёРЅРёСЃС‚СЂР°С‚РѕСЂРѕРІ.',
      'An HTTPS page cannot read a local HTTP API. Open the operator page locally or use an HTTPS API.': 'HTTPS-СЃС‚СЂР°РЅРёС†Р° РЅРµ РјРѕР¶РµС‚ С‡РёС‚Р°С‚СЊ Р»РѕРєР°Р»СЊРЅС‹Р№ HTTP API. РћС‚РєСЂРѕР№С‚Рµ РїР°РЅРµР»СЊ РѕРїРµСЂР°С‚РѕСЂР° Р»РѕРєР°Р»СЊРЅРѕ РёР»Рё РёСЃРїРѕР»СЊР·СѓР№С‚Рµ HTTPS API.',
      'Failed to load operator data.': 'РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РіСЂСѓР·РёС‚СЊ РґР°РЅРЅС‹Рµ РѕРїРµСЂР°С‚РѕСЂР°.',
      'Failed to mark payout.': 'РќРµ СѓРґР°Р»РѕСЃСЊ РѕС‚РјРµС‚РёС‚СЊ РІС‹РїР»Р°С‚Сѓ.',
      'No API connection.': 'РќРµС‚ РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє API.',
      'Bootstrap is blocked. Check ADMIN_VIEW_KEY and migration state.': 'Bootstrap Р·Р°Р±Р»РѕРєРёСЂРѕРІР°РЅ. РџСЂРѕРІРµСЂСЊС‚Рµ ADMIN_VIEW_KEY Рё СЃРѕСЃС‚РѕСЏРЅРёРµ РјРёРіСЂР°С†РёР№.',
      'No active operator session.': 'РќРµС‚ Р°РєС‚РёРІРЅРѕР№ СЃРµСЃСЃРёРё РѕРїРµСЂР°С‚РѕСЂР°.',
      'Intent': 'РљРѕРґ',
      'Wallet': 'РљРѕС€РµР»С‘Рє',
      'Outcome': 'РСЃС…РѕРґ',
      'Amount': 'РЎСѓРјРјР°',
      'Potential payout': 'РџРѕС‚РµРЅС†РёР°Р»СЊРЅР°СЏ РІС‹РїР»Р°С‚Р°',
      'Time': 'Р’СЂРµРјСЏ',
      'Event type': 'РўРёРї СЃРѕР±С‹С‚РёСЏ',
      'Actor': 'РћРїРµСЂР°С‚РѕСЂ',
      'Match state': 'РЎРѕСЃС‚РѕСЏРЅРёРµ РјР°С‚С‡Р°',
      'Extra': 'Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕ',
      'Created': 'РЎРѕР·РґР°РЅ',
      'Last login': 'РџРѕСЃР»РµРґРЅРёР№ РІС…РѕРґ',
      'User ID': 'ID РїРѕР»СЊР·РѕРІР°С‚РµР»СЏ',
      'Active': 'РђРєС‚РёРІРµРЅ',
      'Disabled': 'РћС‚РєР»СЋС‡С‘РЅ',
      'Disable': 'РћС‚РєР»СЋС‡РёС‚СЊ',
      'Enable': 'Р’РєР»СЋС‡РёС‚СЊ',
      'Primary admin': 'Главный администратор',
      'Mark paid': 'РћС‚РјРµС‚РёС‚СЊ РІС‹РїР»Р°С‚Сѓ',
      'Feed size': 'Р Р°Р·РјРµСЂ Р»РµРЅС‚С‹',
      'Accepted': 'РџСЂРёРЅСЏС‚Рѕ',
      'To payout': 'Рљ РІС‹РїР»Р°С‚Рµ',
      'Paid': 'Р’С‹РїР»Р°С‡РµРЅРѕ',
      'Turnover': 'РћР±РѕСЂРѕС‚',
      'No active session.': 'РќРµС‚ Р°РєС‚РёРІРЅРѕР№ СЃРµСЃСЃРёРё.',
      'No bets yet.': 'РџРѕРєР° РЅРµС‚ СЃС‚Р°РІРѕРє.',
      'No audit events yet.': 'РџРѕРєР° РЅРµС‚ СЃРѕР±С‹С‚РёР№ Р°СѓРґРёС‚Р°.',
      'No additional operators yet.': 'РџРѕРєР° РЅРµС‚ РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅС‹С… РѕРїРµСЂР°С‚РѕСЂРѕРІ.',
      'No email assigned': 'Email РЅРµ РЅР°Р·РЅР°С‡РµРЅ',
      'Google Sheets: ON': 'Google Sheets: Р’РљР›',
      'Google Sheets: OFF': 'Google Sheets: Р’Р«РљР›',
      'Operator-side event': 'РЎРѕР±С‹С‚РёРµ СЃРѕ СЃС‚РѕСЂРѕРЅС‹ РѕРїРµСЂР°С‚РѕСЂР°'
    },
    en: {}
  };

  function lang() {
    return (localStorage.getItem(KEY) || 'ru').toLowerCase() === 'en' ? 'en' : 'ru';
  }

  function t(key) {
    const current = lang();
    return (STATIC[current] && STATIC[current][key]) || (STATIC.ru && STATIC.ru[key]) || key;
  }

  function syncStatic() {
    document.documentElement.lang = lang();
    document.title = t('page.title');
    document.querySelectorAll('[data-oi18n]').forEach((el) => {
      el.textContent = t(el.dataset.oi18n);
    });
    document.querySelectorAll('[data-oi18n-placeholder]').forEach((el) => {
      el.setAttribute('placeholder', t(el.dataset.oi18nPlaceholder));
    });
    document.querySelectorAll('[data-lang-option]').forEach((btn) => {
      const active = btn.dataset.langOption === lang();
      btn.classList.toggle('active', active);
      btn.classList.toggle('is-active', active);
    });
  }

  function localizeText(value) {
    if (lang() !== 'ru') return value;
    let out = String(value || '');
    if (EXACT.ru[out]) return EXACT.ru[out];

    out = out.replace(/\(Super admin\)/g, '(РЎСѓРїРµСЂ Р°РґРјРёРЅ)');
    out = out.replace(/\(Operator\)/g, '(РћРїРµСЂР°С‚РѕСЂ)');
    out = out.replace(/\(Finance\)/g, '(Р¤РёРЅР°РЅСЃС‹)');
    out = out.replace(/\(Viewer\)/g, '(РќР°Р±Р»СЋРґР°С‚РµР»СЊ)');
    out = out.replace(/^Copied: (.+)$/u, 'РЎРєРѕРїРёСЂРѕРІР°РЅРѕ: $1');
    out = out.replace(/^Logged in as (.+)\.$/u, 'Р’С…РѕРґ РІС‹РїРѕР»РЅРµРЅ: $1.');
    out = out.replace(/^User (.+) created\.$/u, 'РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ $1 СЃРѕР·РґР°РЅ.');
    out = out.replace(/^User (.+) updated\.$/u, 'РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ $1 РѕР±РЅРѕРІР»С‘РЅ.');
    out = out.replace(/^Bet (.+) marked as paid\.$/u, 'РЎС‚Р°РІРєР° $1 РѕС‚РјРµС‡РµРЅР° РєР°Рє РІС‹РїР»Р°С‡РµРЅРЅР°СЏ.');
    out = out.replace(/^Updated (.+)$/u, 'РћР±РЅРѕРІР»РµРЅРѕ $1');
    out = out.replace(/^(\d+) bets$/u, 'РЎС‚Р°РІРѕРє: $1');
    out = out.replace(/^(\d+) events$/u, 'РЎРѕР±С‹С‚РёР№: $1');
    out = out.replace(/^To payout: (\d+)$/u, 'Рљ РІС‹РїР»Р°С‚Рµ: $1');
    out = out.replace(/^Match #(.+)$/u, 'РњР°С‚С‡ #$1');
    out = out.replace(/^Session active: (.+)\.$/u, 'РЎРµСЃСЃРёСЏ Р°РєС‚РёРІРЅР°: $1.');
    out = out.replace(/^Bootstrap pending\. Owner login: (.+)\. Owner email hint: (.+)\.$/u, 'Bootstrap РѕР¶РёРґР°РµС‚ Р·Р°РІРµСЂС€РµРЅРёСЏ. Р›РѕРіРёРЅ РІР»Р°РґРµР»СЊС†Р°: $1. РџРѕРґСЃРєР°Р·РєР° email: $2.');
    out = out.replace(/^Operator: (.+)$/u, 'РћРїРµСЂР°С‚РѕСЂ: $1');
    return EXACT.ru[out] || out;
  }

  function walk(root) {
    if (lang() !== 'ru') return;
    const walker = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT, null);
    const list = [];
    let node;
    while ((node = walker.nextNode())) {
      if (!node.nodeValue || !node.nodeValue.trim()) continue;
      if (node.parentElement && (node.parentElement.tagName === 'SCRIPT' || node.parentElement.tagName === 'STYLE')) continue;
      list.push(node);
    }
    list.forEach((textNode) => {
      const next = localizeText(textNode.nodeValue);
      if (next !== textNode.nodeValue) {
        textNode.nodeValue = next;
      }
    });
  }

  function patchGlobals() {
    if (typeof formatNumber === 'function') {
      formatNumber = function (value) {
        const num = Number(value || 0);
        return Number.isFinite(num)
          ? num.toLocaleString(lang() === 'en' ? 'en-US' : 'ru-RU', { maximumFractionDigits: 2 })
          : '0';
      };
    }

    if (typeof formatDate === 'function') {
      formatDate = function (value) {
        if (!value) return '-';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return String(value);
        return date.toLocaleString(lang() === 'en' ? 'en-US' : 'ru-RU', {
          timeZone: 'Europe/Moscow',
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
      };
    }

    if (typeof renderStatus === 'function') {
      const oldRenderStatus = renderStatus;
      renderStatus = function (message, tone) {
        oldRenderStatus(localizeText(message), tone);
      };
    }

    if (typeof render === 'function') {
      const oldRender = render;
      render = function () {
        const result = oldRender.apply(this, arguments);
        syncStatic();
        walk(document.body);
        return result;
      };
    }
  }

  function boot() {
    patchGlobals();
    document.querySelectorAll('[data-lang-option]').forEach((btn) => {
      btn.addEventListener('click', () => {
        localStorage.setItem(KEY, btn.dataset.langOption === 'en' ? 'en' : 'ru');
        syncStatic();
        if (typeof render === 'function') render();
      });
    });
    window.addEventListener('storage', (event) => {
      if (event.key === KEY) {
        syncStatic();
        if (typeof render === 'function') render();
      }
    });
    syncStatic();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();


