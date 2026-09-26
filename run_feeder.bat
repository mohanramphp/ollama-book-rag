@echo off
REM run_feeder.bat — activates the project's isolated venv and launches
REM the book-ingestion UI in your browser.

if not exist venv\Scripts\activate.bat (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
streamlit run feeder_app.py
