# stocksRater-Launcher (PowerShell): richtet .venv bei Bedarf ein und fuehrt das Rating aus.
# Aufruf: .\rate.ps1 <TICKER> [TICKER2 ...] [-Json] [-Backtest]
# Alle Parameter werden an python -m src.cli durchgereicht.
$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$py = Join-Path $here ".venv\Scripts\python.exe"
$pyLin = Join-Path $here ".venv/bin/python"

# Python-Findung (Windows: python/py; Linux/macOS mit PowerShell: python3)
function Find-Python {
    foreach ($cmd in @("python", "py", "python3")) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) { return $cmd }
    }
    return $null
}

# --- .venv pruefen/anlegen ---
if (-not (Test-Path $py) -and -not (Test-Path $pyLin)) {
    Write-Host "==> .venv nicht gefunden - erstelle Environment und installiere Dependencies..."
    $python = Find-Python
    if (-not $python) {
        Write-Error "FEHLER: Python nicht gefunden. Bitte Python 3.10+ installieren."
        exit 1
    }
    # 'py' Launcher braucht '-3' fuer den Modus
    if ($python -eq "py") { & $python -3 -m venv .venv } else { & $python -m venv .venv }
    if ($LASTEXITCODE -ne 0) { Write-Error "venv-Erstellung fehlgeschlagen"; exit 1 }

    $pip = if (Test-Path $py) { $py } else { $pyLin }
    & $pip -m pip install --quiet --upgrade pip
    & $pip -m pip install --quiet -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Error "pip-Installation fehlgeschlagen"; exit 1 }
    Write-Host "==> Setup abgeschlossen."
}

# --- Python-Pfad festlegen ---
$venvPython = if (Test-Path $py) { $py } else { $pyLin }

# --- Argumente sortieren: nackte Ticker -> --tickers, Rest 1:1 durchreichen ---
$tickers = ""
$cliArgs = @()
foreach ($a in $args) {
    if ($a -like "-*") { $cliArgs += $a }
    else { if ($tickers) { $tickers = "$tickers,$a" } else { $tickers = $a } }
}

if (-not $tickers) {
    Write-Host "Usage: .\rate.ps1 TICKER [TICKER ...] [--json] [--backtest]"
    Write-Host "Beispiele: .\rate.ps1 AAPL"
    Write-Host "           .\rate.ps1 AAPL MSFT NVDA"
    Write-Host "           .\rate.ps1 AAPL --json"
    exit 1
}

& $venvPython -m src.cli --tickers $tickers @cliArgs
exit $LASTEXITCODE
