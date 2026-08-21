@echo off
echo Starting ChartGen...
cd /d "%~dp0"

REM Check if venv exists, create if not
if not exist "venv\Scripts\activate.bat" (
    echo Setting up virtual environment for the first time...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    REM To add dependencies in future: delete the venv folder and relaunch.
) else (
    call venv\Scripts\activate.bat
)

streamlit run app.py -- %*
