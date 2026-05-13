# PrizmBet v2 - Auto Push QWEN.md Update
# Запуск: .\push-qwen-update.ps1

Write-Host "=== PrizmBet v2 - Push QWEN.md Update ===" -ForegroundColor Cyan

# Проверка Git
$gitVersion = git --version 2>$null
if (-not $gitVersion) {
    Write-Host "[ERROR] Git не установлен. Скачайте с https://git-scm.com/" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Git: $gitVersion" -ForegroundColor Green

# Переход в директорию репозитория
$repoPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoPath
Write-Host "[OK] Directory: $repoPath" -ForegroundColor Green

# Проверка статуса репозитория
Write-Host "`n=== Git Status ===" -ForegroundColor Yellow
git status

# Проверка наличия изменений в QWEN.md
$status = git status --porcelain | Select-String "QWEN.md"
if (-not $status) {
    Write-Host "[WARN] Нет изменений в QWEN.md" -ForegroundColor Yellow
    $createCommit = Read-Host "Создать коммит всё равно? (y/n)"
    if ($createCommit -ne "y") {
        exit 0
    }
}

# Добавление файла
Write-Host "`n=== Adding QWEN.md ===" -ForegroundColor Yellow
git add QWEN.md
Write-Host "[OK] File staged" -ForegroundColor Green

# Коммит
$commitMessage = "docs: update QWEN.md to v2.1 with parser status

- Add actual parser status (Leonbets 1090, OddsAPI.io 41, ApiFootball 30)
- Update performance metrics (real benchmarks)
- Add troubleshooting section
- Add required GitHub Secrets list
- Update improvement priorities
- Add GitHub repository link"

Write-Host "`n=== Committing ===" -ForegroundColor Yellow
git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] Коммит не создан (возможно нет изменений)" -ForegroundColor Yellow
    $forcePush = Read-Host "Продолжить push? (y/n)"
    if ($forcePush -ne "y") {
        exit 0
    }
}

# Пуш
Write-Host "`n=== Pushing to GitHub ===" -ForegroundColor Yellow
Write-Host "Branch: main" -ForegroundColor Cyan

git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] Изменения отправлены на GitHub!" -ForegroundColor Green
    Write-Host "Проверьте: https://github.com/MinorTermite/prizmbet-v2/commit/main" -ForegroundColor Cyan
} else {
    Write-Host "`n[ERROR] Ошибка пуша. Проверьте:" -ForegroundColor Red
    Write-Host "  1. Доступ к интернету" -ForegroundColor Yellow
    Write-Host "  2. Права доступа к репозиторию" -ForegroundColor Yellow
    Write-Host "  3. Настройки Git (git config user.email/user.name)" -ForegroundColor Yellow
    
    $configureGit = Read-Host "`nНастроить Git? (y/n)"
    if ($configureGit -eq "y") {
        $email = Read-Host "Введите email для Git"
        $name = Read-Host "Введите имя для Git"
        
        git config --global user.email $email
        git config --global user.name $name
        
        Write-Host "[OK] Git настроен. Попробуйте push снова:" -ForegroundColor Green
        Write-Host "  .\push-qwen-update.ps1" -ForegroundColor Cyan
    }
}

Write-Host "`n=== Complete ===" -ForegroundColor Cyan
