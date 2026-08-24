@echo off
echo Running ChartGen tests...
cd /d "%~dp0"

REM Same venv the application uses. run_chartgen.bat creates it; this only
REM adds the development-only packages on top, and only if they're missing.
if not exist "venv\Scripts\activate.bat" (
    echo No venv found. Run run_chartgen.bat once first to create it.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat

python -c "import pytest" 2>nul
if errorlevel 1 (
    echo Installing development dependencies...
    pip install -r requirements-dev.txt
)

python -m pytest %*

echo.
echo Tests finished. Note: a green run does NOT mean the app looks right --
echo nothing here checks charts, layout or the interface. Launch ChartGen for that.
pause
