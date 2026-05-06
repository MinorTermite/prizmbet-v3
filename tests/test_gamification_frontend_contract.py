from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CABINET = ROOT / "frontend" / "js" / "modules" / "cabinet_v2.js"
HISTORY_UI = ROOT / "frontend" / "js" / "modules" / "history_ui.js"
SMART_FLOW = ROOT / "frontend" / "css" / "smart-flow.css"
INDEX = ROOT / "frontend" / "index.html"
RULES = ROOT / "frontend" / "rules.html"
ROBOTS = ROOT / "frontend" / "robots.txt"
SITEMAP = ROOT / "frontend" / "sitemap.xml"
BET_SLIP = ROOT / "frontend" / "js" / "modules" / "bet_slip.js"
OPERATOR_HTML = ROOT / "frontend" / "operator.html"
OPERATOR_SHELL = ROOT / "frontend" / "js" / "operator-shell.js"
OPERATOR_CSS = ROOT / "frontend" / "css" / "operator.css"
ANDROID_INDEX = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "index.html"
ANDROID_RULES = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "rules.html"
ANDROID_ROBOTS = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "robots.txt"
ANDROID_SITEMAP = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "sitemap.xml"
ANDROID_CABINET = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "js" / "modules" / "cabinet_v2.js"
ANDROID_HISTORY_UI = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "js" / "modules" / "history_ui.js"
ANDROID_BET_SLIP = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "js" / "modules" / "bet_slip.js"
ANDROID_OPERATOR_HTML = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "operator.html"
ANDROID_OPERATOR_SHELL = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "js" / "operator-shell.js"
ANDROID_SW = ROOT / "prizmbet_android" / "app" / "src" / "main" / "assets" / "prizmbet-v3" / "sw.js"


def test_cabinet_v2_is_wired_into_history_modal():
    history = HISTORY_UI.read_text(encoding="utf-8")
    android_history = ANDROID_HISTORY_UI.read_text(encoding="utf-8")

    for source in (history, android_history):
        assert "import { initCabinetV2, renderGamification } from './cabinet_v2.js';" in source
        assert "initCabinetV2();" in source
        assert "renderGamification(wallet, data)" in source


def test_cabinet_v2_calls_registered_player_api_routes():
    source = CABINET.read_text(encoding="utf-8")
    android_source = ANDROID_CABINET.read_text(encoding="utf-8")

    for module_source in (source, android_source):
        assert "/api/player/${encodeURIComponent(wallet)}" in module_source
        assert "/api/player/${encodeURIComponent(wallet)}/roulette" in module_source
        assert "/api/raffles/active" in module_source
        assert "/api/raffles/${encodeURIComponent(raffle.id)}/enter" in module_source
        assert "method: 'POST'" in module_source
        assert "body: JSON.stringify({ spins })" in module_source
        assert "body: JSON.stringify({ wallet, answers })" in module_source
        assert "raffle:   () => isEn() ? 'Raffle'    : 'Розыгрыш'" in module_source


def test_cabinet_v2_hides_public_mutations_without_wallet_verification():
    source = CABINET.read_text(encoding="utf-8")
    android_source = ANDROID_CABINET.read_text(encoding="utf-8")

    for module_source in (source, android_source):
        assert "function _gamificationMutationsEnabled()" in module_source
        assert "features?.gamification_public_mutations" in module_source
        assert "function _isTabAvailable(tabId)" in module_source
        assert "tabId === 'roulette' || tabId === 'raffle'" in module_source
        assert "].filter(tab => _isTabAvailable(tab.id));" in module_source
        assert "return _lockedMutationHtml(S.tabs.roulette());" in module_source
        assert "return _lockedMutationHtml(S.tabs.raffle());" in module_source


def test_android_shell_caches_cabinet_v2_module():
    sw = ANDROID_SW.read_text(encoding="utf-8")

    assert "./js/modules/cabinet_v2.js" in sw


def test_cabinet_v2_keeps_russian_utf8_strings_readable():
    source = CABINET.read_text(encoding="utf-8")

    for text in (
        "Статистика",
        "Задания",
        "Бонусы",
        "Рулетка",
        "Введите кошелёк",
        "Ошибка рулетки",
    ):
        assert text in source


def test_cabinet_v2_has_required_styles():
    css = SMART_FLOW.read_text(encoding="utf-8")

    for selector in (
        ".cv2-panel",
        ".cv2-hero",
        ".cv2-tabs",
        ".cv2-tab-btn.is-active",
        ".cv2-progress-fill",
        ".cv2-quest-card",
        ".cv2-quest-meta",
        ".cv2-quest-reward",
        ".cv2-bonus-card",
        ".cv2-roulette",
        ".cv2-spin-btn",
        ".cv2-prize-row",
        ".cv2-raffle",
        ".cv2-raffle-question",
        ".cv2-raffle-submit",
    ):
        assert selector in css


def test_express_coupon_ui_is_present():
    html = INDEX.read_text(encoding="utf-8")
    css = SMART_FLOW.read_text(encoding="utf-8")

    for marker in (
        "bsExpressBuilder",
        "bsExpressSummary",
        "bsAddExpressBtn",
        "bsClearExpressBtn",
        "bsExpressList",
    ):
        assert marker in html

    for selector in (
        ".express-builder",
        ".express-builder-head",
        ".express-leg-list",
        ".express-leg",
        ".express-leg-remove",
    ):
        assert selector in css


def test_express_coupon_posts_backend_contract():
    source = BET_SLIP.read_text(encoding="utf-8")

    assert "const EXPRESS_MAX_LEGS = 12;" in source
    assert "const EXPRESS_ODDS_CAP = 100;" in source
    assert "DUPLICATE_MATCH_IN_EXPRESS" in source
    assert "function getExpressOdds" in source
    assert "function isExpressReady" in source
    assert "function sameExpressLegs" in source
    assert "bet_type: 'express'" in source
    assert "legs: form.legs" in source
    assert "apiOutcome: expressReady ? 'EXPRESS'" in source


def test_android_assets_include_express_coupon_contract():
    html = ANDROID_INDEX.read_text(encoding="utf-8")
    source = ANDROID_BET_SLIP.read_text(encoding="utf-8")

    assert "bsExpressBuilder" in html
    assert "const EXPRESS_MAX_LEGS = 12;" in source
    assert "bet_type: 'express'" in source
    assert "legs: form.legs" in source


def test_public_rules_page_documents_gamification_contract():
    html = RULES.read_text(encoding="utf-8")
    android_html = ANDROID_RULES.read_text(encoding="utf-8")
    css = SMART_FLOW.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    android_index = ANDROID_INDEX.read_text(encoding="utf-8")

    for text in (
        "Правила уровней, заданий и наград",
        "11 уровней игрока",
        "Футбольный патриот",
        "1 / 1 000",
        "Временный миллионер +0.5% на 7 дней",
        "Персонаж растёт вместе с уровнем",
        "2 000 000 000 PRIZM",
        "Розыгрыши",
    ):
        assert text in html
        assert text in android_html

    for removed_text in (
        "10 000 000 000 PRIZM",
        "100 000 000 000 PRIZM",
        "1 000 000 000 000 PRIZM",
        "10 000 000 000 000 PRIZM",
        "PRIZM / USDT",
        "Отличие валют",
    ):
        assert removed_text not in html
        assert removed_text not in android_html

    for selector in (
        ".gamification-rules-page",
        ".gamification-rules-hero",
        ".gamification-rules-grid",
        ".rules-level-table",
        ".rules-prize-table",
        ".rules-mascot-grid",
        ".rules-mascot-figure",
    ):
        assert selector in css

    assert 'data-i18n="footer.rules" href="./rules.html"' in index
    assert 'data-i18n="footer.rules" href="./rules.html"' in android_index


def test_public_pages_include_basic_seo_contract():
    index = INDEX.read_text(encoding="utf-8")
    android_index = ANDROID_INDEX.read_text(encoding="utf-8")
    rules = RULES.read_text(encoding="utf-8")
    android_rules = ANDROID_RULES.read_text(encoding="utf-8")
    robots = ROBOTS.read_text(encoding="utf-8")
    android_robots = ANDROID_ROBOTS.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    android_sitemap = ANDROID_SITEMAP.read_text(encoding="utf-8")

    for source in (index, android_index):
        assert "<title>1PrizmBet — ставки на спорт в PRIZM</title>" in source
        assert 'alt="1PrizmBet" width="1916" height="821"' in source
        assert 'name="twitter:title"' in source
        assert '"@type":"WebSite"' in source

    for source in (rules, android_rules):
        assert "<title>1PrizmBet — правила уровней, заданий и наград</title>" in source
        assert 'rel="canonical"' in source
        assert 'property="og:title"' in source
        assert 'name="twitter:title"' in source
        assert '"@type":"WebPage"' in source
        assert '"@type":"BreadcrumbList"' in source
        assert 'alt="1PrizmBet" width="1916" height="821"' in source

    for source in (robots, android_robots):
        assert "User-agent: *" in source
        assert "Sitemap: https://prizmbet.net/sitemap.xml" in source

    for source in (sitemap, android_sitemap):
        assert "<loc>https://prizmbet.net/</loc>" in source
        assert "<loc>https://prizmbet.net/rules.html</loc>" in source


def test_operator_gamification_admin_contract():
    html = OPERATOR_HTML.read_text(encoding="utf-8")
    source = OPERATOR_SHELL.read_text(encoding="utf-8")
    css = OPERATOR_CSS.read_text(encoding="utf-8")
    android_html = ANDROID_OPERATOR_HTML.read_text(encoding="utf-8")
    android_source = ANDROID_OPERATOR_SHELL.read_text(encoding="utf-8")

    for marker in (
        'data-operator-tab="gamification"',
        'id="gamificationSection"',
        'id="weeklyStartInput"',
        'id="finalizeWeeklyBtn"',
        'id="raffleQuestionsInput"',
        'id="createRaffleBtn"',
        'id="gameWalletInput"',
        'id="creditGameSessionBtn"',
    ):
        assert marker in html
        assert marker in android_html

    for marker in (
        "/api/admin/leaderboard/weekly/finalize",
        "/api/admin/raffles",
        "/api/admin/player/${encodeURIComponent(wallet)}/game-session",
        "questions.length !== 11",
        "weekly_leaderboard_finalized",
        "raffle_created",
        "game_session_credited",
        "gamification: 'Геймификация'",
    ):
        assert marker in source
        assert marker in android_source

    for selector in (
        ".operator-gamification-section",
        ".operator-textarea",
        ".operator-admin-list",
        "[data-active-tab='gamification']",
    ):
        assert selector in css
