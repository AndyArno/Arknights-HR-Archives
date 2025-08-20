@echo off
REM 更简洁的启动脚本
ECHO Checking for requirements.txt...
IF NOT EXIST requirements.txt (
    ECHO Error: requirements.txt not found!
    timeout /t 5
    exit /b 1
)

ECHO Installing/Updating dependencies...
pip install -r requirements.txt

ECHO Starting application...
pythonw app.py

ECHO Application started in background.
timeout /t 2
exit
