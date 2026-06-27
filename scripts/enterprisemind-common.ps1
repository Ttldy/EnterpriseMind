Set-StrictMode -Version 2.0

function Get-EnterpriseMindRoot {
    $candidate = Split-Path -Parent $PSScriptRoot
    while ($candidate -and (Test-Path -LiteralPath $candidate)) {
        $compose = Join-Path $candidate "compose.dev.yml"
        $backendMain = Join-Path $candidate "backend\app\main.py"
        if ((Test-Path -LiteralPath $compose) -and (Test-Path -LiteralPath $backendMain)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
        $parent = Split-Path -Parent $candidate
        if ($parent -eq $candidate) {
            break
        }
        $candidate = $parent
    }
    throw "Cannot locate EnterpriseMind project root."
}

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Write-Ok {
    param([string]$Message)
    Write-Host "[OK] $Message"
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[FAIL] $Message" -ForegroundColor Red
}

function Test-CommandExists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Test-CondaEnv {
    param([string]$Name)
    if (-not (Test-CommandExists "conda")) {
        return $false
    }
    $envs = & conda env list 2>$null
    if ($LASTEXITCODE -ne 0) {
        return $false
    }
    foreach ($line in $envs) {
        if ($line -match ("(^|\s)" + [regex]::Escape($Name) + "(\s|\*)")) {
            return $true
        }
    }
    return $false
}

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutMilliseconds = 800
    )
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne($TimeoutMilliseconds, $false)
        if (-not $connected) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function ConvertTo-PowerShellSingleQuoted {
    param([string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Invoke-ExternalStep {
    param(
        [string]$Name,
        [scriptblock]$Command
    )
    Write-Step $Name
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE."
    }
    Write-Ok $Name
}

function Show-DefaultAccounts {
    Write-Host ""
    Write-Host "Demo accounts seeded by backend\scripts\seed_stage1.py:"
    Write-Host "  admin      / AdminPassw0rd!      Admin console"
    Write-Host "  it01       / ItPassw0rd!         IT assistant"
    Write-Host "  hr01       / HrPassw0rd!         HR assistant"
    Write-Host "  finance01 / FinancePassw0rd!    Finance and data query"
    Write-Host "  employee01/ EmployeePassw0rd!   Permission isolation demo"
}
