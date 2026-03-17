(function () {
  const KEY = 'prizmbet_lang_v1';
  const STATIC = {
    ru: {
      'page.title': 'PRIZMBET - Кабинет оператора',
      'hero.eyebrow': 'Кабинет оператора',
      'hero.title': 'Ставки, пользователи и аудит',
      'hero.copy': 'Панель работает на именованных аккаунтах операторов. Владелец фиксируется один раз, а действия по ставкам и выплатам привязаны к конкретной пользовательской сессии.',
      'hero.back': 'Вернуться на сайт',
      'access.apiBase': 'API base',
      'access.apiBasePlaceholder': 'https://your-backend.example',
      'access.connect': 'Подключить',
      'access.refresh': 'Обновить',
      'access.autoRefresh': 'Автообновление',
      'bootstrap.eyebrow': 'Bootstrap владельца',
      'bootstrap.title': 'Создать единственного super admin',
      'bootstrap.copy': 'Этот шаг работает только один раз и только для заранее заданной личности владельца.',
      'bootstrap.email': 'Email владельца',
      'bootstrap.emailPlaceholder': 'owner@example.com',
      'bootstrap.login': 'Логин владельца',
      'bootstrap.loginPlaceholder': 'owner',
      'bootstrap.password': 'Пароль',
      'bootstrap.passwordPlaceholder': 'Минимум 8 символов',
      'bootstrap.key': 'Bootstrap key',
      'bootstrap.keyPlaceholder': 'ADMIN_VIEW_KEY из .env',
      'bootstrap.action': 'Создать owner-аккаунт',
      'login.eyebrow': 'Вход',
      'login.title': 'Войти как оператор',
      'login.copy': 'Используйте назначенный логин или email и свой пароль.',
      'login.identity': 'Логин или email',
      'login.identityPlaceholder': 'owner или name@example.com',
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
      'users.copy': 'Только владелец может создавать и отключать операторские аккаунты.',
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
      'hero.title': 'Bets, users and audit trail',
      'hero.copy': 'This panel runs on named operator accounts. The owner identity is fixed once, and all bet and payout actions stay tied to a specific user session.',
      'hero.back': 'Back to site',
      'access.apiBase': 'API base',
      'access.apiBasePlaceholder': 'https://your-backend.example',
      'access.connect': 'Connect',
      'access.refresh': 'Refresh',
      'access.autoRefresh': 'Auto refresh',
      'bootstrap.eyebrow': 'Owner Bootstrap',
      'bootstrap.title': 'Create the only super admin',
      'bootstrap.copy': 'This step works only once and only for the configured owner identity.',
      'bootstrap.email': 'Owner email',
      'bootstrap.emailPlaceholder': 'owner@example.com',
      'bootstrap.login': 'Owner login',
      'bootstrap.loginPlaceholder': 'owner',
      'bootstrap.password': 'Password',
      'bootstrap.passwordPlaceholder': 'Minimum 8 characters',
      'bootstrap.key': 'Bootstrap key',
      'bootstrap.keyPlaceholder': 'ADMIN_VIEW_KEY from .env',
      'bootstrap.action': 'Create owner account',
      'login.eyebrow': 'Login',
      'login.title': 'Enter as operator',
      'login.copy': 'Use the assigned login or email and your password.',
      'login.identity': 'Login or email',
      'login.identityPlaceholder': 'owner or name@example.com',
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
      'users.copy': 'Only the owner can create or disable operator accounts.',
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
      'Set API base and connect.': 'Укажите API base и подключитесь.',
      'Set API base first.': 'Сначала укажите API base.',
      'Connect to inspect the operator auth state.': 'Подключитесь, чтобы проверить состояние авторизации операторов.',
      'Checking operator access...': 'Проверяю доступ оператора...',
      'Auth state is unknown.': 'Состояние авторизации неизвестно.',
      'Feed not loaded yet.': 'Лента ещё не загружена.',
      'Audit log not loaded yet.': 'Журнал аудита ещё не загружен.',
      'Failed to copy value to clipboard.': 'Не удалось скопировать значение в буфер обмена.',
      'Failed to read bootstrap state.': 'Не удалось прочитать состояние bootstrap.',
      'Admin session is invalid.': 'Сессия администратора недействительна.',
      'Owner email, login, password and bootstrap key are required.': 'Нужны email владельца, логин, пароль и bootstrap key.',
      'Owner account created. Session is active.': 'Аккаунт владельца создан. Сессия активна.',
      'Failed to bootstrap owner account.': 'Не удалось создать аккаунт владельца.',
      'Login/email and password are required.': 'Нужны логин или email и пароль.',
      'Failed to log in.': 'Не удалось войти.',
      'Only the super admin can create users.': 'Только super admin может создавать пользователей.',
      'Failed to create user.': 'Не удалось создать пользователя.',
      'Failed to update user state.': 'Не удалось обновить состояние пользователя.',
      'Failed to load admin users.': 'Не удалось загрузить список администраторов.',
      'An HTTPS page cannot read a local HTTP API. Open the operator page locally or use an HTTPS API.': 'HTTPS-страница не может читать локальный HTTP API. Откройте панель оператора локально или используйте HTTPS API.',
      'Failed to load operator data.': 'Не удалось загрузить данные оператора.',
      'Failed to mark payout.': 'Не удалось отметить выплату.',
      'No API connection.': 'Нет подключения к API.',
      'Bootstrap is blocked. Check ADMIN_VIEW_KEY and migration state.': 'Bootstrap заблокирован. Проверьте ADMIN_VIEW_KEY и состояние миграций.',
      'No active operator session.': 'Нет активной сессии оператора.',
      'Intent': 'Код',
      'Wallet': 'Кошелёк',
      'Outcome': 'Исход',
      'Amount': 'Сумма',
      'Potential payout': 'Потенциальная выплата',
      'Time': 'Время',
      'Event type': 'Тип события',
      'Actor': 'Оператор',
      'Match state': 'Состояние матча',
      'Extra': 'Дополнительно',
      'Created': 'Создан',
      'Last login': 'Последний вход',
      'User ID': 'ID пользователя',
      'Active': 'Активен',
      'Disabled': 'Отключён',
      'Disable': 'Отключить',
      'Enable': 'Включить',
      'Owner': 'Владелец',
      'Mark paid': 'Отметить выплату',
      'Feed size': 'Размер ленты',
      'Accepted': 'Принято',
      'To payout': 'К выплате',
      'Paid': 'Выплачено',
      'Turnover': 'Оборот',
      'No active session.': 'Нет активной сессии.',
      'No bets yet.': 'Пока нет ставок.',
      'No audit events yet.': 'Пока нет событий аудита.',
      'No additional operators yet.': 'Пока нет дополнительных операторов.',
      'No email assigned': 'Email не назначен',
      'Google Sheets: ON': 'Google Sheets: ВКЛ',
      'Google Sheets: OFF': 'Google Sheets: ВЫКЛ',
      'Operator-side event': 'Событие со стороны оператора'
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

    out = out.replace(/\(Super admin\)/g, '(Супер админ)');
    out = out.replace(/\(Operator\)/g, '(Оператор)');
    out = out.replace(/\(Finance\)/g, '(Финансы)');
    out = out.replace(/\(Viewer\)/g, '(Наблюдатель)');
    out = out.replace(/^Copied: (.+)$/u, 'Скопировано: $1');
    out = out.replace(/^Logged in as (.+)\.$/u, 'Вход выполнен: $1.');
    out = out.replace(/^User (.+) created\.$/u, 'Пользователь $1 создан.');
    out = out.replace(/^User (.+) updated\.$/u, 'Пользователь $1 обновлён.');
    out = out.replace(/^Bet (.+) marked as paid\.$/u, 'Ставка $1 отмечена как выплаченная.');
    out = out.replace(/^Updated (.+)$/u, 'Обновлено $1');
    out = out.replace(/^(\d+) bets$/u, 'Ставок: $1');
    out = out.replace(/^(\d+) events$/u, 'Событий: $1');
    out = out.replace(/^To payout: (\d+)$/u, 'К выплате: $1');
    out = out.replace(/^Match #(.+)$/u, 'Матч #$1');
    out = out.replace(/^Session active: (.+)\.$/u, 'Сессия активна: $1.');
    out = out.replace(/^Bootstrap pending\. Owner login: (.+)\. Owner email hint: (.+)\.$/u, 'Bootstrap ожидает завершения. Логин владельца: $1. Подсказка email: $2.');
    out = out.replace(/^Operator: (.+)$/u, 'Оператор: $1');
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
