@echo off
REM run_query.bat — activates the project's isolated venv and launches
REM the chat UI in your browser.

if not exist venv\Scripts\activate.bat (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
streamlit run query_app.py
