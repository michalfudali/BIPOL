@echo off
title BIPOL Studio - Server
cd /d "%~dp0"
echo ========================================================
echo   Uruchamianie serwera BIPOL Studio (MEiL PW)
echo   Adres lokalny: http://127.0.0.1:5000
echo   Zatrzymanie: Ctrl + C
echo ========================================================
py -3.14 app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Proba uruchomienia przez 'py app.py'...
    py app.py
    if %ERRORLEVEL% NEQ 0 (
        echo Proba uruchomienia przez 'python'...
        python app.py
    )
)
pause
