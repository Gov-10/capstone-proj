# Start Legal Summarizer Services
Write-Host "Starting Legal Summarizer Services..." -ForegroundColor Green
Write-Host ""

$pythonPath = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python311\python.exe"
$nodePath = "C:\Program Files\nodejs\node.exe"

# Check if Python is available
if (-not (Test-Path $pythonPath)) {
    Write-Host "Error: Python not found at $pythonPath" -ForegroundColor Red
    exit 1
}

# Check if Node is available
if (-not (Test-Path $nodePath)) {
    Write-Host "Error: Node.js not found at $nodePath" -ForegroundColor Red
    exit 1
}

# Terminal 1: Django Backend
Write-Host "Terminal 1: Starting Django Backend on port 8000..." -ForegroundColor Cyan
$djangoProcess = Start-Process -FilePath $pythonPath `
    -ArgumentList "manage.py", "runserver", "0.0.0.0:8000" `
    -WorkingDirectory "$PSScriptRoot\django_back" `
    -NoNewWindow `
    -PassThru

Write-Host "Django Backend PID: $($djangoProcess.Id)" -ForegroundColor Gray

# Wait a moment
Start-Sleep -Seconds 2

# Terminal 2: FastAPI Backend
Write-Host "Terminal 2: Starting FastAPI Backend on port 8080..." -ForegroundColor Cyan
$fastApiProcess = Start-Process -FilePath $pythonPath `
    -ArgumentList "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--reload" `
    -WorkingDirectory "$PSScriptRoot\fastapi_agents" `
    -NoNewWindow `
    -PassThru

Write-Host "FastAPI Backend PID: $($fastApiProcess.Id)" -ForegroundColor Gray

# Wait a moment
Start-Sleep -Seconds 2

# Terminal 3: NextJS Frontend
Write-Host "Terminal 3: Starting NextJS Frontend on port 3000..." -ForegroundColor Cyan
$frontendProcess = Start-Process -FilePath $nodePath `
    -ArgumentList "C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js", "run", "dev" `
    -WorkingDirectory "$PSScriptRoot\front" `
    -NoNewWindow `
    -PassThru

Write-Host "Frontend PID: $($frontendProcess.Id)" -ForegroundColor Gray

Write-Host ""
Write-Host "All services started successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Services running on:" -ForegroundColor Yellow
Write-Host "  - Django Backend: http://localhost:8000" -ForegroundColor White
Write-Host "  - FastAPI Backend: http://localhost:8080/docs" -ForegroundColor White
Write-Host "  - NextJS Frontend: http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Gray

# Wait for processes
$djangoProcess.WaitForExit()
$fastApiProcess.WaitForExit()
$frontendProcess.WaitForExit()
