@echo off
REM setup.bat — creates a self-contained virtual environment for this project
REM and installs only the packages this project needs into it. Run this once.

echo Creating virtual environment in .\venv ...
if exist venv\Scripts\python.exe goto venv_ready

if exist venv (
    echo An incomplete virtual environment already exists in .\venv.
    echo Close any Python or Streamlit processes using it, then remove .\venv and run setup.bat again.
    exit /b 1
)

py -m venv venv
if errorlevel 1 (
    echo Failed to create the virtual environment.
    exit /b 1
)

:venv_ready

if not exist venv\Scripts\activate.bat (
    echo Failed to create virtual environment. Is Python installed and on PATH?
    exit /b 1
)

echo Activating virtual environment and installing dependencies...
call venv\Scripts\activate.bat
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo Done. The virtual environment is at .\venv and has only this project's
echo packages installed - nothing was touched globally.
echo.
echo Next steps:
echo   1. Pull the models this project needs:
echo        ollama pull phi4-mini
echo        ollama pull nomic-embed-text
echo   2. Run run_knowledge_builder.bat to add knowledge sources, or run_query.bat to chat.
echo.
pause
