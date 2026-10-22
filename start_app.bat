@echo off
title BIPOL Studio - Server (Python 3.11)
cd /d "%~dp0"
echo ========================================================
echo   Uruchamianie serwera BIPOL Studio (MEiL PW)
echo   Srodowisko: Python 3.11
echo   Adres lokalny: http://127.0.0.1:5000
echo   Zatrzymanie: Ctrl + C
echo ========================================================
py -3.11 app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Proba uruchomienia przez 'python app.py'...
    python app.py
    if %ERRORLEVEL% NEQ 0 (
        echo Proba uruchomienia przez 'py app.py'...
        py app.py
        if %ERRORLEVEL% NEQ 0 (
            echo.
            echo [BLAD] Nie udalo sie uruchomic aplikacji.
            echo Upewnij sie, ze Python 3.11 oraz zaleznosci sa zainstalowane:
            echo   py -3.11 -m pip install -r requirements.txt
        )
    )
)
pause
