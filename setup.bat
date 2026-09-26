@echo off
REM setup.bat — creates a self-contained virtual environment for this project
REM and installs only the packages this project needs into it. Run this once.

echo Creating virtual environment in .\venv ...
py -m venv venv

if not exist venv\Scripts\activate.bat (
    echo Failed to create virtual environment. Is Python installed and on PATH?
    exit /b 1
)

echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

echo.
echo Done. The virtual environment is at .\venv and has only this project's
echo packages installed - nothing was touched globally.
echo.
echo Next steps:
echo   1. Pull the models this project needs:
echo        ollama pull phi4-mini
echo        ollama pull nomic-embed-text
echo   2. Run run_feeder.bat to ingest books, or run_query.bat to chat.
echo.
pause
