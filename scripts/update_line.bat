@echo off
echo ==========================================
echo   PRIZMBET: ОБНОВЛЕНИЕ ЛИНИИ (ЛОКАЛЬНО)
echo ==========================================
echo 1. Получение последних изменений с GitHub...
git pull origin main

echo.
echo 2. Запуск парсеров (это может занять 1-2 минуты)...
python backend/api/generate_json.py

echo.
echo 3. Обогащение счетами матчей...
python backend/score_enricher.py

echo.
echo 4. Отправка обновленных данных на сайт...
git add frontend/matches.json
git commit -m "chore(data): manual line update %date% %time%"
git push origin main

echo.
echo ==========================================
echo   ГОТОВО! Данные обновлены и отправлены.
echo ==========================================
pause
