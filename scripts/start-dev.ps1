param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$StartupTimeoutSeconds = 15
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $Root "backend"
$FrontendDir = Join-Path $Root "frontend"
$LogDir = Join-Path $Root "logs"
$DefaultDataDir = Join-Path $Root "data"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Repair-ProcessPathEnvironment {
    $effectivePath = [Environment]::GetEnvironmentVariable("Path", "Process")
    if (-not $effectivePath) {
        return
    }

    [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
    [Environment]::SetEnvironmentVariable("Path", $effectivePath, "Process")
}

function Set-DevDataEnvironment {
    $dataDir = [Environment]::GetEnvironmentVariable("QUANT_LAB_DATA_DIR", "Process")
    if (-not $dataDir) {
        $dataDir = $DefaultDataDir
    }

    if (-not [System.IO.Path]::IsPathRooted($dataDir)) {
        $dataDir = Join-Path $Root $dataDir
    }

    $databasePath = [Environment]::GetEnvironmentVariable("QUANT_LAB_DATABASE_PATH", "Process")
    if (-not $databasePath) {
        $databasePath = Join-Path $dataDir "quant_lab.sqlite3"
    }
    elseif (-not [System.IO.Path]::IsPathRooted($databasePath)) {
        $databasePath = Join-Path $Root $databasePath
    }

    $instrumentDataDir = [Environment]::GetEnvironmentVariable("QUANT_LAB_INSTRUMENT_DATA_DIR", "Process")
    if (-not $instrumentDataDir) {
        $instrumentDataDir = Join-Path $dataDir "instruments"
    }
    elseif (-not [System.IO.Path]::IsPathRooted($instrumentDataDir)) {
        $instrumentDataDir = Join-Path $Root $instrumentDataDir
    }

    New-Item -ItemType Directory -Force -Path $dataDir, $instrumentDataDir, (Split-Path -Parent $databasePath) | Out-Null
    [Environment]::SetEnvironmentVariable("DATA_DIR", $dataDir, "Process")
    [Environment]::SetEnvironmentVariable("DATABASE_PATH", $databasePath, "Process")
    [Environment]::SetEnvironmentVariable("INSTRUMENT_DATA_DIR", $instrumentDataDir, "Process")

    return [PSCustomObject]@{
        DataDir = $dataDir
        DatabasePath = $databasePath
        InstrumentDataDir = $instrumentDataDir
    }
}

function Get-CommandPath {
    param(
        [string[]]$Names,
        [string]$EnvName
    )

    $envValue = [Environment]::GetEnvironmentVariable($EnvName)
    if ($envValue) {
        return $envValue
    }

    foreach ($name in $Names) {
        $command = Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($command) {
            return $command.Source
        }
    }

    throw "Cannot find command: $($Names -join ', ')"
}

function Test-PortInUse {
    param([int]$Port)

    $connection = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" } |
        Select-Object -First 1

    return $null -ne $connection
}

function Wait-ForPort {
    param(
        [int]$Port,
        [string]$ServiceName,
        [int]$TimeoutSeconds
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortInUse $Port) {
            return
        }

        Start-Sleep -Milliseconds 250
    }

    throw "$ServiceName did not begin listening on port $Port within $TimeoutSeconds seconds. Check the logs in $LogDir."
}

function Start-DevProcess {
    param(
        [string]$Title,
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$WorkingDirectory,
        [string]$OutLog,
        [string]$ErrLog,
        [string]$PidFile
    )

    $process = Start-Process `
        -PassThru `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -RedirectStandardOutput $OutLog `
        -RedirectStandardError $ErrLog `
        -WindowStyle Hidden

    Set-Content -LiteralPath $PidFile -Value $process.Id -Encoding ASCII
}

Repair-ProcessPathEnvironment
$devData = Set-DevDataEnvironment

if (Test-PortInUse $BackendPort) {
    Write-Host "Backend port $BackendPort is already in use; leaving it running."
}
else {
    $python = Get-CommandPath -Names @("python.exe", "python") -EnvName "QUANT_LAB_PYTHON"
    $backendOut = Join-Path $LogDir "backend-dev.out.log"
    $backendErr = Join-Path $LogDir "backend-dev.err.log"
    $backendPid = Join-Path $LogDir "backend-dev.pid"

    Start-DevProcess `
        -Title "Quant Lab Backend" `
        -FilePath $python `
        -ArgumentList @("-m", "flask", "--app", "wsgi", "run", "--host", "127.0.0.1", "--port", $BackendPort) `
        -WorkingDirectory $BackendDir `
        -OutLog $backendOut `
        -ErrLog $backendErr `
        -PidFile $backendPid
    Wait-ForPort -Port $BackendPort -ServiceName "Backend" -TimeoutSeconds $StartupTimeoutSeconds
    Write-Host "Started backend on http://127.0.0.1:$BackendPort"
}

if (Test-PortInUse $FrontendPort) {
    Write-Host "Frontend port $FrontendPort is already in use; leaving it running."
}
else {
    $npm = Get-CommandPath -Names @("npm.cmd", "npm") -EnvName "QUANT_LAB_NPM"
    $frontendOut = Join-Path $LogDir "frontend-dev.out.log"
    $frontendErr = Join-Path $LogDir "frontend-dev.err.log"
    $frontendPid = Join-Path $LogDir "frontend-dev.pid"

    Start-DevProcess `
        -Title "Quant Lab Frontend" `
        -FilePath $npm `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", $FrontendPort) `
        -WorkingDirectory $FrontendDir `
        -OutLog $frontendOut `
        -ErrLog $frontendErr `
        -PidFile $frontendPid
    Wait-ForPort -Port $FrontendPort -ServiceName "Frontend" -TimeoutSeconds $StartupTimeoutSeconds
    Write-Host "Started frontend on http://127.0.0.1:$FrontendPort"
}

Write-Host ""
Write-Host "Data: $($devData.DatabasePath)"
Write-Host "Logs:"
Write-Host "  $LogDir\backend-dev.err.log"
Write-Host "  $LogDir\frontend-dev.out.log"
Write-Host ""
Write-Host "Open: http://127.0.0.1:$FrontendPort"
