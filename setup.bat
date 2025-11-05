@echo off
setlocal

echo Checking Python installation...

python --version >nul 2>&1

if errorlevel 1 (
    echo Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from https://www.python.org/downloads
    exit /b 1
)

for /f "tokens=2 delims= " %%a in ('python --version 2^>^&1') do set "PY_VER=%%a"

for /f "tokens=1,2,3 delims=." %%a in ("%PY_VER%") do (
    set "MAJOR=%%a"
    set "MINOR=%%b"
)

if %MAJOR% LSS 3 (
    echo Python version %PY_VER% is too old. Please install 3.8 or higher.
    exit /b 1
)

if %MAJOR% EQU 3 if %MINOR% LSS 8 (
    echo Python version %PY_VER% is too old. Please install 3.8 or higher.
    exit /b 1
)

echo Python %PY_VER% detected - OK!

echo Creating virtual environment .venv

if exist .venv (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        exit /b 1
    )
)

call .venv/Scripts/activate.bat

if errorlevel 1 (
    echo Failed to activate virtual environment.
    exit /b 1
)

echo Installing requirements
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo Failed to install dependencies.
    exit /b 1
)

echo Dependencies installed.

if not exist .env (
    echo Creating .env file
    copy /y .env.sample .env >nul
    echo .env file created.
)

echo.
echo Setup complete! To run the program from here:
echo 1. Open the file .env and input your API token next to DISCORD_BOT_TOKEN, no spaces.
echo 2. To activate the python environment, run .venv/Scripts/activate in powershell (or call .venv\Scripts\activate.bat in command prompt)
echo 3. Start the program with python main.py

pause

endlocal
