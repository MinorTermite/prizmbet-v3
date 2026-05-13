// ==========================================
// PRIZMBET SMOKE TESTS
// Легковесные assert-проверки для защиты критического пути
// ==========================================

function runSmokeTests() {
    console.log('[Tests] Запуск базовых Smoke Tests...');

    // 1. Проверка API функций (загружены ли они из api.js)
    console.assert(typeof window.loadData === 'function', '[Ошибка] loadData не найдена. api.js не загружен?');

    // 3. Проверка Купона Ставок (Bet Slip DOM и логика)
    const bs = document.getElementById('betSlip');
    console.assert(bs !== null, '[Ошибка] DOM-элемент #betSlip не найден!');
    const bsInput = document.getElementById('bsInput');
    console.assert(bsInput !== null, '[Ошибка] Поле ввода #bsInput не найдено!');

    // 4. Проверка предотвращения множественных рендеров (Diff check preparedness)
    const content = document.getElementById('content');
    console.assert(content !== null, '[Ошибка] Контейнер #content не найден.');

    console.log('[Tests] Проверки завершены ✅');
}

// Запускаем после загрузки DOM и начального рендера
window.addEventListener('load', () => {
    setTimeout(runSmokeTests, 2000);
});
