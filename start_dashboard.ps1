# Start backend
Write-Host "Starting Facebook Work Notifier Dashboard..." -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/2] Starting Backend API..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; uvicorn app.main:app --reload --port 8001"
Start-Sleep -Seconds 3

Write-Host ""
Write-Host "[2/2] Starting Frontend Dashboard..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "Dashboard starting up..." -ForegroundColor Green
Write-Host "Backend: http://localhost:8001" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5174" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press any key to stop all servers..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host ""
Write-Host "Stopping servers..." -ForegroundColor Yellow
Get-Process | Where-Object {$_.MainWindowTitle -like "*Backend API*" -or $_.MainWindowTitle -like "*Frontend Dashboard*"} | Stop-Process -Force
Write-Host "Done!" -ForegroundColor Green
