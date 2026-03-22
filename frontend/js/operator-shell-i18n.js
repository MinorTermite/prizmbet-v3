(function () {
  const KEY = 'prizmbet_lang_v1';

  const STATIC = {
    ru: {
      'page.title': 'PRIZMBET - Кабинет оператора',
      'hero.eyebrow': 'Кабинет оператора',
      'hero.title': 'Ставки, пользователи и аудит',
      'hero.copy': 'Компактная рабочая панель для ставок, выплат и аудита.',
      'hero.back': 'Вернуться на сайт',
      'access.apiBase': 'API base',
      'access.apiBasePlaceholder': 'https://your-backend.example',
      'access.connect': 'Подключить',
      'access.refresh': 'Обновить',
      'access.autoRefresh': 'Автообновление',
      'bootstrap.eyebrow': 'Первичная настройка',
      'bootstrap.title': 'Создать администратора',
      'bootstrap.copy': 'Этот шаг выполняется один раз для первичной настройки панели.',
      'bootstrap.email': 'Email администратора',
      'bootstrap.emailPlaceholder': 'admin@example.com',
      'bootstrap.login': 'Логин администратора',
      'bootstrap.loginPlaceholder': 'admin',
      'bootstrap.password': 'Пароль',
      'bootstrap.passwordPlaceholder': 'Минимум 8 символов',
      'bootstrap.key': 'Bootstrap key',
      'bootstrap.keyPlaceholder': 'ADMIN_VIEW_KEY из .env',
      'bootstrap.action': 'Создать аккаунт',
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
      'users.copy': 'Создание и управление операторскими аккаунтами.',
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
      'hero.title': 'Bets, users and audit',
      'hero.copy': 'Compact workspace for bets, payouts and audit.',
      'hero.back': 'Back to site',
      'access.apiBase': 'API base',
      'access.apiBasePlaceholder': 'https://your-backend.example',
      'access.connect': 'Connect',
      'access.refresh': 'Refresh',
      'access.autoRefresh': 'Auto refresh',
      'bootstrap.eyebrow': 'Initial setup',
      'bootstrap.title': 'Create administrator',
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
      'login.title': 'Log in as operator',
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
      'users.eyebrow': 'User management',
      'users.title': 'Assigned operators',
      'users.copy': 'Create and manage operator accounts.',
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
      'feed.searchPlaceholder': 'Search by match, TX, wallet, code or league',
      'statusFilter.all': 'All statuses',
      'status.accepted': 'Accepted',
      'status.rejected': 'Rejected',
      'status.won': 'Won',
      'status.lost': 'Lost',
      'status.refund_pending': 'Refund pending',
      'status.paid': 'Paid',
      'audit.eyebrow': 'Audit log',
      'audit.title': 'Recent backend and operator events',
      'audit.copy': 'Accepted, rejected, settled and paid bets are logged here. If the webhook is enabled, the same events can also be mirrored to Google Sheets.'
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
      'Administrator email, login, password and bootstrap key are required.': 'Нужны email администратора, логин, пароль и bootstrap key.',
      'Administrator account created. Session is active.': 'Аккаунт администратора создан. Сессия активна.',
      'Failed to bootstrap administrator account.': 'Не удалось создать аккаунт администратора.',
      'Login/email and password are required.': 'Нужны логин или email и пароль.',
      'Failed to log in.': 'Не удалось войти.',
      'Only the super admin can create users.': 'Только главный админ может создавать пользователей.',
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
      'Primary admin': 'Главный админ',
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

    out = out.replace(/\(Super admin\)/g, '(Админ)');
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
    out = out.replace(/^Bootstrap pending\. Owner login: (.+)\. Owner email hint: (.+)\.$/u, 'Ожидается первичная настройка. Логин администратора: $1. Email-подсказка: $2.');
    out = out.replace(/^Operator: (.+)$/u, 'Оператор: $1');
    return EXACT.ru[out] || out;
  }

  function walk(root) {
    if (lang() !== 'ru') return;
    const walker = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT, null);
    const nodes = [];
    let node;
    while ((node = walker.nextNode())) {
      if (!node.nodeValue || !node.nodeValue.trim()) continue;
      if (node.parentElement && (node.parentElement.tagName === 'SCRIPT' || node.parentElement.tagName === 'STYLE')) continue;
      nodes.push(node);
    }
    nodes.forEach((textNode) => {
      const next = localizeText(textNode.nodeValue);
      if (next !== textNode.nodeValue) textNode.nodeValue = next;
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