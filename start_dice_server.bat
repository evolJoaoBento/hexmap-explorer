@echo off
echo Starting Dice Roll API Server...
echo ================================
echo Server will run on http://localhost:5001
echo Press Ctrl+C to stop the server
echo ================================
echo.

REM Set environment variables if needed
set FLASK_ENV=development
set DICE_SERVER_PORT=5001

REM Start the dice server
python dice_server.py

pause