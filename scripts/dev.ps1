[CmdletBinding()]
param(
    [switch]$Stop,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$workspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendDir = Join-Path $workspaceRoot "backend"
$frontendDir = Join-Path $workspaceRoot "frontend"
$devDir = Join-Path $workspaceRoot ".dev"
$statePath = Join-Path $devDir "processes.json"
$backendUrl = "http://127.0.0.1:8000/api/health"
$frontendUrl = "http://127.0.0.1:3000"

function Test-ProcessAlive {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return $false }
    return $null -ne (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)
}

function Stop-DevProcessTree {
    param([int]$RootProcessId)
    if ($RootProcessId -le 0) { return }

    $children = @(
        Get-CimInstance Win32_Process -Filter "ParentProcessId = $RootProcessId" -ErrorAction SilentlyContinue
    )
    foreach ($child in $children) {
        Stop-DevProcessTree -RootProcessId ([int]$child.ProcessId)
    }

    if (Test-ProcessAlive -ProcessId $RootProcessId) {
        Stop-Process -Id $RootProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Test-Url {
    param([string]$Url)
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Wait-ForUrl {
    param(
        [string]$Url,
        [string]$Name,
        [int]$TimeoutSeconds = 45
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Url -Url $Url) { return }
        Start-Sleep -Milliseconds 400
    }
    throw "$Name khong san sang sau $TimeoutSeconds giay: $Url"
}

function Show-LogTail {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        Write-Host "`n--- $Path ---" -ForegroundColor DarkYellow
        Get-Content -LiteralPath $Path -Tail 40
    }
}

if ($Stop) {
    if (-not (Test-Path -LiteralPath $statePath)) {
        Write-Host "Khong co phien dev nao do launcher quan ly." -ForegroundColor Yellow
        exit 0
    }

    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    Stop-DevProcessTree -RootProcessId ([int]$state.frontend_pid)
    Stop-DevProcessTree -RootProcessId ([int]$state.backend_pid)
    Remove-Item -LiteralPath $statePath -Force
    Write-Host "Da dung backend va frontend dev." -ForegroundColor Green
    exit 0
}

New-Item -ItemType Directory -Path $devDir -Force | Out-Null

$pythonPath = (Get-Command python -ErrorAction Stop).Source
$nodePath = (Get-Command node -ErrorAction Stop).Source
$viteEntry = Join-Path $frontendDir "node_modules\vite\bin\vite.js"
if (-not (Test-Path -LiteralPath $viteEntry)) {
    throw "Thieu frontend/node_modules. Chay: npm --prefix frontend install"
}

$previousState = $null
if (Test-Path -LiteralPath $statePath) {
    try {
        $previousState = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    }
    catch {
        $previousState = $null
    }
}

$backendPid = 0
$frontendPid = 0
$startedBackendPid = 0
$startedFrontendPid = 0

if ($previousState) {
    if (Test-ProcessAlive -ProcessId ([int]$previousState.backend_pid)) {
        $backendPid = [int]$previousState.backend_pid
    }
    if (Test-ProcessAlive -ProcessId ([int]$previousState.frontend_pid)) {
        $frontendPid = [int]$previousState.frontend_pid
    }
}

$backendOut = Join-Path $devDir "backend.out.log"
$backendErr = Join-Path $devDir "backend.err.log"
$frontendOut = Join-Path $devDir "frontend.out.log"
$frontendErr = Join-Path $devDir "frontend.err.log"

try {
    if (-not (Test-Url -Url $backendUrl)) {
        $backendProcess = Start-Process `
            -FilePath $pythonPath `
            -ArgumentList @(
                "-m", "uvicorn", "main:app",
                "--app-dir", $backendDir,
                "--host", "127.0.0.1",
                "--port", "8000",
                "--reload",
                "--reload-dir", $backendDir
            ) `
            -WorkingDirectory $workspaceRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $backendOut `
            -RedirectStandardError $backendErr `
            -PassThru
        $backendPid = $backendProcess.Id
        $startedBackendPid = $backendPid
    }
    Wait-ForUrl -Url $backendUrl -Name "FastAPI backend"

    if (-not (Test-Url -Url $frontendUrl)) {
        $frontendProcess = Start-Process `
            -FilePath $nodePath `
            -ArgumentList @(
                $viteEntry,
                "--host", "127.0.0.1",
                "--port", "3000",
                "--strictPort"
            ) `
            -WorkingDirectory $frontendDir `
            -WindowStyle Hidden `
            -RedirectStandardOutput $frontendOut `
            -RedirectStandardError $frontendErr `
            -PassThru
        $frontendPid = $frontendProcess.Id
        $startedFrontendPid = $frontendPid
    }
    Wait-ForUrl -Url $frontendUrl -Name "Vite frontend"

    @{
        backend_pid = $backendPid
        frontend_pid = $frontendPid
        started_at = (Get-Date).ToString("o")
        app_url = $frontendUrl
    } | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
}
catch {
    Stop-DevProcessTree -RootProcessId $startedFrontendPid
    Stop-DevProcessTree -RootProcessId $startedBackendPid
    Show-LogTail -Path $backendErr
    Show-LogTail -Path $frontendErr
    throw
}

Write-Host "Dev app da san sang:" -ForegroundColor Green
Write-Host "  App:       $frontendUrl"
Write-Host "  API docs:  http://127.0.0.1:8000/docs"
Write-Host "  OBS scene: http://127.0.0.1:8000/static/scene/index.html"
Write-Host "  Logs:      $devDir"
Write-Host "Dung bang: npm run dev:stop" -ForegroundColor Cyan

if (-not $NoBrowser) {
    $browserCandidates = @(
        (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
        (Join-Path $env:LocalAppData "Google\Chrome\Application\chrome.exe")
    )
    $appBrowser = $browserCandidates | Where-Object {
        $_ -and (Test-Path -LiteralPath $_)
    } | Select-Object -First 1

    if ($appBrowser) {
        Start-Process -FilePath $appBrowser -ArgumentList @("--app=$frontendUrl", "--new-window") | Out-Null
    }
    else {
        Start-Process $frontendUrl | Out-Null
    }
}
