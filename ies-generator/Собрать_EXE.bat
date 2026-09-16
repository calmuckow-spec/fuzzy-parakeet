@echo off
chcp 65001 >nul
title Сборка IES_Generator.exe

echo ============================================================
echo   Сборка программы IES_Generator.exe
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден.
    echo.
    echo Установите Python 3.11 или новее с сайта python.org
    echo и обязательно отметьте галочку "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

echo [1/3] Установка нужных библиотек...
python -m pip install --upgrade pip
python -m pip install openpyxl pyinstaller
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Не удалось установить библиотеки. Проверьте интернет.
    pause
    exit /b 1
)

echo.
echo [2/3] Сборка исполняемого файла...
python -m PyInstaller --onefile --windowed --clean ^
    --name IES_Generator ^
    --hidden-import openpyxl ^
    --hidden-import openpyxl.styles ^
    --hidden-import openpyxl.utils ^
    ies_app.py
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Сборка не удалась. Скопируйте текст выше и покажите его.
    pause
    exit /b 1
)

echo.
echo [3/3] Готово.
echo.
echo Программа лежит здесь:  %CD%\dist\IES_Generator.exe
echo Этот файл можно скопировать на любой компьютер с Windows.
echo.
pause
