const LANG_KEY = 'prizmbet_lang_v1';
const DEFAULT_LANG = 'ru';

const DICTIONARY = {
    ru: {
        'app.tagline': 'Прогнозы на PRIZM',
        'header.timeLabel': 'Московское время',
        'header.timeShort': 'MSK',
        'header.notifications': 'Уведомления',
        'header.telegram': 'Telegram',
        'header.cabinet': 'Кабинет',
        'header.refresh': 'Обновить линию',
        'header.download': 'Скачать APK',
        'header.menu': 'Меню',
        'header.lang': 'Язык',
        'header.menuTitle': 'Быстрые действия',
        'header.liveLine': 'Линия событий',
        'hero.eyebrow': 'Prizmbet',
        'hero.title': 'Линия, купон и статус в одном приложении',
        'hero.subtitle': 'Выберите матч, откройте купон и отслеживайте расчёт в кабинете кошелька.',
        'hero.trustOddsTitle': 'Потенциальная выплата',
        'hero.trustOddsCopy': 'Сумма × коэффициент = ожидаемая выплата по купону.',
        'hero.trustWindowTitle': 'Ограниченное окно',
        'hero.trustWindowCopy': 'Перевод должен прийти до старта события и внутри окна купона.',
        'hero.trustStatusTitle': 'Статус в кабинете',
        'hero.trustStatusCopy': 'Кошелёк показывает ожидание, принятие, отклонение и расчёт.',
        'hero.trustPayoutTitle': 'Выплаты до 24 часов',
        'hero.trustPayoutCopy': 'Корректные выигрышные прогнозы обрабатываются по правилам проекта.',
        'hero.events': 'Событий в линии',
        'hero.leagues': 'Доступных лиг',
        'hero.avgOdds': 'Средний коэффициент',
        'hero.cabinet': 'Открыть кабинет',
        'hero.telegram': 'Telegram',
        'quick.eyebrow': 'Как это работает',
        'quick.title': '3 шага от матча до статуса',
        'quick.copy': 'Главный экран ведёт к действию, а правила перевода собраны в отдельном компактном блоке.',
        'quick.step1Title': 'Выберите исход',
        'quick.step1Copy': 'Нажмите на коэффициент в линии, чтобы открыть купон.',
        'quick.step2Title': 'Выпустите код',
        'quick.step2Copy': 'Укажите кошелёк и сумму. Купон зафиксирует параметры прогноза.',
        'quick.step3Title': 'Проверьте статус',
        'quick.step3Copy': 'После перевода откройте кабинет и отслеживайте принятие и расчёт.',
        'quick.note': 'Потенциальная выплата считается прозрачно: сумма × коэффициент. Система проверяет событие, исход, сумму и кошелёк.',
        'search.placeholder': 'Поиск команды, лиги или ID матча...',
        'tabs.all': 'Все',
        'tabs.football': 'Футбол',
        'tabs.hockey': 'Хоккей',
        'tabs.basket': 'Баскетбол',
        'tabs.tennis': 'Теннис',
        'tabs.volleyball': 'Волейбол',
        'tabs.esports': 'Киберспорт',
        'tabs.mma': 'MMA',
        'tabs.totals': 'Тоталы',
        'tabs.results': 'Результаты',
        'tabs.favs': 'Избранное',
        'filters.allLeagues': 'Все лиги',
        'filters.topOnly': 'Только топ',
        'filters.date': 'Дата:',
        'filters.allDates': 'Все',
        'filters.today': 'Сегодня',
        'filters.tomorrow': 'Завтра',
        'filters.later': 'Дальше',
        'filters.sort': 'Сортировка:',
        'filters.defaultSort': 'По умолч.',
        'filters.byTime': 'По времени',
        'filters.byOdds': 'По коэф.',
        'filters.byLeague': 'По лигам',
        'filters.loading': 'Загрузка...',
        'wallet.title': 'Шаг 2. Перевод по коду',
        'wallet.addressLabel': 'Кошелёк проекта',
        'wallet.copy': 'Скопировать кошелёк',
        'wallet.note': 'Сначала выпустите код в купоне. Затем отправьте перевод на кошелёк проекта и укажите этот код в сообщении.',
        'rules.eyebrow': 'Перед переводом',
        'rules.title': '3 правила приёма перевода',
        'rules.copy': 'Здесь собраны только ключевые проверки prematch-прогноза и перевода.',
        'rules.codeTitle': 'Код купона',
        'rules.codeCopy': 'В переводе должен быть действующий код из выпущенного купона.',
        'rules.walletTitle': 'Кошелёк и окно времени',
        'rules.walletCopy': 'Перевод должен прийти с того же PRIZM-адреса и до старта события.',
        'rules.limitsTitle': 'Лимиты и расчёт',
        'rules.limitsCopy': 'Публичная версия принимает только prematch-прогнозы в лимитах и с корректным кодом.',
        'rules.min': 'Мин: 1 500 PRIZM',
        'rules.max': 'Макс: 30 000 PRIZM',
        'rules.payout': 'Выплаты до 24 часов',
        'footer.copy': 'Информационный сервис по спортивным событиям. Сайт отображает линию, статусы и данные по прогнозам внутри экосистемы проекта.',
        'toast.brand': 'Prizmbet',
        'coupon.title': 'Умный купон',
        'coupon.wallet': 'Кошелёк игрока',
        'coupon.amount': 'Сумма',
        'coupon.expected': 'Ожидаемая сумма:',
        'coupon.payout': 'Потенциальная выплата:',
        'coupon.window': 'До 15 минут на выпуск и перевод',
        'coupon.ready': 'Купон готов',
        'coupon.issue': 'Выпустить код',
        'coupon.copyCode': 'Скопировать код',
        'coupon.lockTitle': 'Что фиксирует этот код',
        'coupon.event': 'Событие',
        'coupon.outcome': 'Исход',
        'coupon.odds': 'Коэффициент',
        'coupon.amountFixed': 'Сумма',
        'coupon.payoutFixed': 'Потенциальная выплата',
        'coupon.expires': 'Код действует до',
        'coupon.nextStep': 'Следующий шаг',
        'coupon.refreshStatus': 'Обновить статус',
        'coupon.openCabinet': 'Открыть кабинет',
        'coupon.timeline': 'Лента статуса',
        'cabinet.title': 'Кабинет кошелька',
        'cabinet.wallet': 'Кошелёк игрока',
        'cabinet.refresh': 'Обновить кабинет',
        'cabinet.clear': 'Очистить историю устройства',
        'cabinet.source': 'Источник статуса',
        'cabinet.rank': 'Текущий уровень',
        'status.draft': 'Черновик',
        'status.awaiting_payment': 'Ждёт перевод',
        'status.accepted': 'Принята',
        'status.rejected': 'Отклонена',
        'status.expired': 'Истекла',
        'status.won': 'Выиграла',
        'status.lost': 'Проиграла',
        'status.finished': 'Завершён',
        'status.live': 'LIVE',
        'status.imminent': 'Старт < 15 мин',
        'rank.start': 'Начинающий игрок',
        'rank.player': 'Игрок',
        'rank.tactic': 'Постоянный игрок',
        'rank.pro': 'Профи',
        'rank.emperor': 'Мастер',
        'common.team1': 'Команда 1',
        'common.team2': 'Команда 2',
        'common.shareMatch': 'Ссылка на матч скопирована.',
        'common.addFavorite': 'Добавлено в избранное',
        'common.removeFavorite': 'Удалено из избранного',
        'common.notificationsOn': 'Уведомления включены',
        'common.loadingLine': 'Загружаем линию...',
        'common.loadingCabinet': 'Загружаем кабинет кошелька...',
        'common.matchesNotFound': 'Матчи не найдены',
        'common.noLeague': 'Без лиги',
        'common.openMatch': 'Открыть матч',
        'common.liveCenter': 'Live-центр',
        'common.mainMarkets': 'Основные исходы',
        'common.doubleChance': 'Двойной шанс',
        'common.total': 'Тотал',
        'common.totalOver': 'ТБ {value}',
        'common.totalUnder': 'ТМ {value}',
        'common.todayLabel': 'Сегодня',
        'common.loadingErrorTitle': 'Не удалось загрузить матчи',
        'common.loadingErrorText': 'Проверьте подключение и попробуйте ещё раз',
        'common.retry': 'Повторить',
        'common.updatedAt': 'Обновлено: {value}',
        'common.cache': 'кэш',
        'common.line': 'линия',
        'common.full': 'полный',
        'common.archiveSnapshot': 'архивный срез',
        'common.archivedEyebrow': 'Архивный срез линии',
        'common.archivedTitle': 'Свежий фид сейчас недоступен, поэтому сайт показывает последний сохранённый срез.',
        'common.archivedCount': 'Сейчас показан последний доступный снимок: {count} событий.',
        'common.archivedTime': 'Последнее обновление: {time}.',
        'common.archivedFallback': 'Время обновления взято из локального кэша устройства.',
        'common.archivedEmpty': 'В текущем окне нет свежих матчей. Попробуйте позже или откройте полный фид.',
        'common.matchFinishedTitle': 'Матч завершён'
    },
    en: {
        'app.tagline': 'Predictions on PRIZM',
        'header.timeLabel': 'Moscow time',
        'header.timeShort': 'MSK',
        'header.notifications': 'Notifications',
        'header.telegram': 'Telegram',
        'header.cabinet': 'Cabinet',
        'header.refresh': 'Refresh line',
        'header.download': 'Download APK',
        'header.menu': 'Menu',
        'header.lang': 'Language',
        'header.menuTitle': 'Quick actions',
        'header.liveLine': 'Events line',
        'hero.eyebrow': 'Prizmbet',
        'hero.title': 'Line, coupon and status in one app',
        'hero.subtitle': 'Pick a match, open the coupon and track settlement in the wallet cabinet.',
        'hero.trustOddsTitle': 'Potential payout',
        'hero.trustOddsCopy': 'Amount × odds = the expected payout locked in the coupon.',
        'hero.trustWindowTitle': 'Limited window',
        'hero.trustWindowCopy': 'The transfer must arrive before kickoff and within the coupon window.',
        'hero.trustStatusTitle': 'Status in cabinet',
        'hero.trustStatusCopy': 'The wallet shows waiting, accepted, rejected and settled states.',
        'hero.trustPayoutTitle': 'Payouts within 24h',
        'hero.trustPayoutCopy': 'Valid winning predictions are processed under project rules.',
        'hero.events': 'Events in line',
        'hero.leagues': 'Leagues available',
        'hero.avgOdds': 'Average odds',
        'hero.cabinet': 'Open cabinet',
        'hero.telegram': 'Telegram',
        'quick.eyebrow': 'How it works',
        'quick.title': '3 steps from match to status',
        'quick.copy': 'The home screen drives action, while transfer rules stay in a compact block below.',
        'quick.step1Title': 'Pick an outcome',
        'quick.step1Copy': 'Tap an odds button in the line to open the coupon.',
        'quick.step2Title': 'Issue the code',
        'quick.step2Copy': 'Enter the wallet and amount. The coupon will lock the parameters and show the payout.',
        'quick.step3Title': 'Check the status',
        'quick.step3Copy': 'After the transfer, open the cabinet and watch acceptance and settlement.',
        'quick.note': 'The payout is transparent: amount × odds. The system validates the event, outcome, amount and wallet.',
        'search.placeholder': 'Search by team, league or match ID...',
        'tabs.all': 'All',
        'tabs.football': 'Football',
        'tabs.hockey': 'Hockey',
        'tabs.basket': 'Basketball',
        'tabs.tennis': 'Tennis',
        'tabs.volleyball': 'Volleyball',
        'tabs.esports': 'Esports',
        'tabs.mma': 'MMA',
        'tabs.totals': 'Totals',
        'tabs.results': 'Results',
        'tabs.favs': 'Favorites',
        'filters.allLeagues': 'All leagues',
        'filters.topOnly': 'Top only',
        'filters.date': 'Date:',
        'filters.allDates': 'All',
        'filters.today': 'Today',
        'filters.tomorrow': 'Tomorrow',
        'filters.later': 'Later',
        'filters.sort': 'Sort:',
        'filters.defaultSort': 'Default',
        'filters.byTime': 'By time',
        'filters.byOdds': 'By odds',
        'filters.byLeague': 'By league',
        'filters.loading': 'Loading...',
        'wallet.title': 'Step 2. Transfer by code',
        'wallet.addressLabel': 'Project wallet',
        'wallet.copy': 'Copy wallet',
        'wallet.note': 'Issue the code in the coupon first. Then send the transfer to the project wallet and put this code in the message.',
        'rules.eyebrow': 'Before the transfer',
        'rules.title': '3 rules that decide acceptance',
        'rules.copy': 'Only the core prematch transfer checks stay here.',
        'rules.codeTitle': 'Coupon code',
        'rules.codeCopy': 'The transfer must include a valid code from an issued coupon.',
        'rules.walletTitle': 'Wallet and time window',
        'rules.walletCopy': 'The transfer must come from the same PRIZM address and before the event starts.',
        'rules.limitsTitle': 'Limits and settlement',
        'rules.limitsCopy': 'The public version accepts prematch predictions only, within limits and with a valid code.',
        'rules.min': 'Min: 1,500 PRIZM',
        'rules.max': 'Max: 30,000 PRIZM',
        'rules.payout': 'Payouts within 24h',
        'footer.copy': 'An information and analytics portal for sports events. The service shows the line, statuses and prediction data inside the project ecosystem.',
        'toast.brand': 'Prizmbet',
        'coupon.title': 'Smart coupon',
        'coupon.wallet': 'Player wallet',
        'coupon.amount': 'Amount',
        'coupon.expected': 'Expected amount:',
        'coupon.payout': 'Potential payout:',
        'coupon.window': 'Up to 15 minutes to issue and transfer',
        'coupon.ready': 'Coupon ready',
        'coupon.issue': 'Issue code',
        'coupon.copyCode': 'Copy code',
        'coupon.lockTitle': 'What this code locks',
        'coupon.event': 'Event',
        'coupon.outcome': 'Outcome',
        'coupon.odds': 'Odds',
        'coupon.amountFixed': 'Amount',
        'coupon.payoutFixed': 'Potential payout',
        'coupon.expires': 'Code valid until',
        'coupon.nextStep': 'Next step',
        'coupon.refreshStatus': 'Refresh status',
        'coupon.openCabinet': 'Open cabinet',
        'coupon.timeline': 'Status timeline',
        'cabinet.title': 'Wallet cabinet',
        'cabinet.wallet': 'Player wallet',
        'cabinet.refresh': 'Refresh cabinet',
        'cabinet.clear': 'Clear device history',
        'cabinet.source': 'Status source',
        'cabinet.rank': 'Current level',
        'status.draft': 'Draft',
        'status.awaiting_payment': 'Waiting for transfer',
        'status.accepted': 'Accepted',
        'status.rejected': 'Rejected',
        'status.expired': 'Expired',
        'status.won': 'Won',
        'status.lost': 'Lost',
        'status.finished': 'Finished',
        'status.live': 'LIVE',
        'status.imminent': 'Starts < 15 min',
        'rank.start': 'Beginner',
        'rank.player': 'Player',
        'rank.tactic': 'Regular',
        'rank.pro': 'Pro',
        'rank.emperor': 'Master',
        'common.team1': 'Team 1',
        'common.team2': 'Team 2',
        'common.shareMatch': 'Match link copied.',
        'common.addFavorite': 'Added to favorites',
        'common.removeFavorite': 'Removed from favorites',
        'common.notificationsOn': 'Notifications enabled',
        'common.loadingLine': 'Loading line...',
        'common.loadingCabinet': 'Loading wallet cabinet...',
        'common.matchesNotFound': 'No matches found',
        'common.noLeague': 'No league',
        'common.openMatch': 'Open match',
        'common.liveCenter': 'Live center',
        'common.mainMarkets': 'Main outcomes',
        'common.doubleChance': 'Double chance',
        'common.total': 'Total',
        'common.totalOver': 'Over {value}',
        'common.totalUnder': 'Under {value}',
        'common.todayLabel': 'Today',
        'common.loadingErrorTitle': 'Failed to load matches',
        'common.loadingErrorText': 'Check your internet connection',
        'common.retry': 'Retry',
        'common.updatedAt': 'Updated: {value}',
        'common.cache': 'cache',
        'common.line': 'line',
        'common.full': 'full',
        'common.archiveSnapshot': 'archived snapshot',
        'common.archivedEyebrow': 'Archived line snapshot',
        'common.archivedTitle': 'The live feed is unavailable, so the site shows the last saved snapshot.',
        'common.archivedCount': 'The latest available snapshot is shown now: {count} events.',
        'common.archivedTime': 'Last update: {time}.',
        'common.archivedFallback': 'The last update time was kept in local cache.',
        'common.archivedEmpty': 'There are no fresh matches in the current window. Check back later or open the full feed.',
        'common.matchFinishedTitle': 'Match finished'
    }
};

function interpolate(template, vars = {}) {
    return String(template || '').replace(/\{(\w+)\}/g, (_, key) => String(vars[key] ?? ''));
}

export function getLanguage() {
    const raw = String(localStorage.getItem(LANG_KEY) || DEFAULT_LANG).toLowerCase();
    return raw === 'en' ? 'en' : 'ru';
}

export function setLanguage(lang) {
    const next = lang === 'en' ? 'en' : 'ru';
    localStorage.setItem(LANG_KEY, next);
    document.documentElement.lang = next;
    applyTranslations();
    window.dispatchEvent(new CustomEvent('prizmbet:language-changed', { detail: { lang: next } }));
    return next;
}

export function getLocale() {
    return getLanguage() === 'en' ? 'en-US' : 'ru-RU';
}

export function getTimeZone() {
    return 'Europe/Moscow';
}

export function t(key, vars = {}) {
    const lang = getLanguage();
    const table = DICTIONARY[lang] || DICTIONARY[DEFAULT_LANG];
    const fallback = DICTIONARY[DEFAULT_LANG];
    return interpolate(table[key] ?? fallback[key] ?? key, vars);
}

export function formatNumber(value, options = {}) {
    const number = Number(value ?? 0);
    if (!Number.isFinite(number)) return '0';
    return number.toLocaleString(getLocale(), options);
}

export function formatDateTime(value, options = {}) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return String(value || '');
    return date.toLocaleString(getLocale(), {
        timeZone: getTimeZone(),
        day: '2-digit',
        month: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        ...options,
    });
}

export function formatDate(value, options = {}) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return String(value || '');
    return date.toLocaleDateString(getLocale(), {
        timeZone: getTimeZone(),
        ...options,
    });
}

export function formatTime(value, options = {}) {
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return String(value || '');
    return date.toLocaleTimeString(getLocale(), {
        timeZone: getTimeZone(),
        hour: '2-digit',
        minute: '2-digit',
        ...options,
    });
}

export function formatOutcomeLabel(label) {
    const raw = String(label || '').trim();
    if (getLanguage() === 'ru') return raw;
    const upper = raw.toUpperCase();
    if (upper === 'П1') return 'P1';
    if (upper === 'П2') return 'P2';
    if (upper.startsWith('ТБ ')) return t('common.totalOver', { value: raw.replace(/^ТБ\s+/u, '') });
    if (upper.startsWith('ТМ ')) return t('common.totalUnder', { value: raw.replace(/^ТМ\s+/u, '') });
    return raw;
}

export function applyTranslations(root = document) {
    const lang = getLanguage();
    document.documentElement.lang = lang;
    root.querySelectorAll('[data-i18n]').forEach((el) => {
        el.textContent = t(el.dataset.i18n);
    });
    root.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
        el.setAttribute('placeholder', t(el.dataset.i18nPlaceholder));
    });
    root.querySelectorAll('[data-i18n-title]').forEach((el) => {
        el.setAttribute('title', t(el.dataset.i18nTitle));
    });
    root.querySelectorAll('[data-i18n-aria]').forEach((el) => {
        el.setAttribute('aria-label', t(el.dataset.i18nAria));
    });
    root.querySelectorAll('[data-lang-option]').forEach((el) => {
        el.classList.toggle('is-active', el.dataset.langOption === lang);
    });
}
