@echo off
echo Testing Hex Map Explorer...
echo.
cd /d "C:\Users\joaoo\hexcrawl"
echo Current directory: %CD%
echo.
echo Testing Python...
"C:\Program Files\Python311\python.exe" --version
echo.
echo Launching main_menu.py...
"C:\Program Files\Python311\python.exe" main_menu.py
echo.
echo Python finished with exit code: %ERRORLEVEL%
if %ERRORLEVEL% neq 0 (
    echo *** ERROR OCCURRED ***
    echo Check the output above for error messages.
) else (
    echo Game closed normally.
)
echo.
pause
