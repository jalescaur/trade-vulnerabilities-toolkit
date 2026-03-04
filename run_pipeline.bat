@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem ============================================================
rem run_pipeline.bat (Windows-compatible: no wmic, no tee)
rem ============================================================
rem Usage:
rem   .\run_pipeline.bat
rem   .\run_pipeline.bat configs\default.yaml
rem ============================================================

rem ---- Config path (argument or default) ----
set "CONFIG_PATH=%~1"
if "%CONFIG_PATH%"=="" set "CONFIG_PATH=configs\default.yaml"

rem ---- Validate repo root ----
call :log "[0] Validating repository root..."
if not exist pyproject.toml (
  call :log "ERROR: pyproject.toml not found. Run this .bat from the repo root."
  exit /b 1
)
if not exist scripts\run_all.py (
  call :log "ERROR: scripts\run_all.py not found. Run this .bat from the repo root."
  exit /b 1
)
if not exist "%CONFIG_PATH%" (
  call :log "ERROR: Config file not found: %CONFIG_PATH%"
  exit /b 1
)

rem ---- Ensure logs directory ----
if not exist outputs\logs mkdir outputs\logs >nul 2>&1

rem ---- Timestamp via PowerShell (no wmic dependency) ----
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%i"
set "LOGFILE=outputs\logs\bat_run_%TS%.log"

call :log "Logging to: %LOGFILE%"
call :log "Config: %CONFIG_PATH%"

rem ---- Check Python ----
call :log "[1] Checking Python..."
python --version >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  call :log "ERROR: Python not found in PATH. Install Python and restart terminal."
  exit /b 1
)
python --version

rem ---- Create venv if needed ----
call :log "[2] Creating/using virtual environment (.venv)..."
if not exist .venv (
  call :log "- .venv not found. Creating..."
  python -m venv .venv >> "%LOGFILE%" 2>&1
  if errorlevel 1 (
    call :log "ERROR: Failed to create venv. See log: %LOGFILE%"
    exit /b 1
  )
) else (
  call :log "- .venv already exists."
)

rem ---- Activate venv ----
call :log "[3] Activating virtual environment..."
call .venv\Scripts\activate.bat >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  call :log "ERROR: Failed to activate .venv. See log: %LOGFILE%"
  exit /b 1
)

rem ---- Upgrade pip ----
call :log "[4] Upgrading pip..."
python -m pip install --upgrade pip >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  call :log "ERROR: pip upgrade failed. See log: %LOGFILE%"
  exit /b 1
)
python -m pip --version

rem ---- Install project editable ----
call :log "[5] Installing project (editable): pip install -e ."
python -m pip install -e . >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  call :log "ERROR: pip install -e . failed. See log: %LOGFILE%"
  exit /b 1
)

rem ---- Environment check ----
call :log "[6] Running environment check..."
python scripts\00_check_environment.py --config "%CONFIG_PATH%" >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  call :log "ERROR: Environment check failed. See log: %LOGFILE%"
  exit /b 1
)

rem ---- Run full pipeline with analysis ----
call :log "[7] Running full pipeline (constructors + analysis)..."
python scripts\run_all.py --config "%CONFIG_PATH%" --include-analysis >> "%LOGFILE%" 2>&1
if errorlevel 1 (
  call :log "ERROR: Pipeline failed. See log: %LOGFILE%"
  exit /b 1
)

call :log "✅ DONE."
call :log "Outputs:"
call :log "- Chapter tables: outputs\tables\"
call :log "- Exploratory excels: data\processed\exploratory_excels\"
call :log "- Exploratory figures PDF: data\processed\exploratory_figures\metrics_exploratory.pdf"
call :log "- Log file: %LOGFILE%"
echo.
exit /b 0

rem ============================================================
rem Logger function: prints to console AND appends to logfile
rem ============================================================
:log
echo %~1
>> "%LOGFILE%" echo %~1
exit /b 0