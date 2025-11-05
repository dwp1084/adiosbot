@echo off

if not exist .venv (
    echo Virtual environment not found.
    echo Run setup.bat before running this script.
    exit /b 1
)

call .venv\Scripts\activate.bat

if errorlevel 1 (
    echo Failed to activate virtual environment.
    exit /b 1
)

echo Activate virtual environment - OK

if not exist .env (
    echo .env file not found. Please copy .env.sample and rename it to .env,
    echo then put your API token next to DISCORD_BOT_TOKEN.
    exit /b 1
)

echo .env exists - OK
echo Starting the bot...

python main.py
