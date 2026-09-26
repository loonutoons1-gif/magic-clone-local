@echo off
setlocal
cd /d "%~dp0"

echo ======================================
echo Magic Clone Local - Windows Launcher
echo ======================================

python --version >nul 2>&1
if errorlevel 1 (
  echo Python is not installed or not on PATH.
  echo Install Python 3.10+ from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

if "%HF_TOKEN%"=="" (
  echo.
  echo HF_TOKEN is not set.
  echo Set it once in PowerShell, then reopen this launcher:
  echo   setx HF_TOKEN "hf_your_token_here"
  echo.
  echo You can continue now, but Hugging Face requests will likely fail.
  echo.
)

echo Installing/updating dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

echo Starting app...
python magic_clone.py
if errorlevel 1 (
  echo App exited with an error.
  pause
  exit /b 1
)

endlocal
