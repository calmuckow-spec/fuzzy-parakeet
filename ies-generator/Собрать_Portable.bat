@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title Сборка портативной версии IES_Generator
cd /d "%~dp0"

echo ============================================================
echo   Сборка портативной версии (папка, без установки)
echo ============================================================
echo.
echo Этот вариант собирает папку dist\IES_Generator со всеми файлами.
echo Всю папку можно заархивировать (zip) и передать на другой компьютер:
echo там её нужно просто распаковать и запустить IES_Generator.exe —
echo без установки Python и без предупреждений антивируса, характерных
echo для однофайловой сборки.
echo.

set PYCMD=
where python >nul 2>&1
if not errorlevel 1 set PYCMD=python
if not defined PYCMD (
    where py >nul 2>&1
    if not errorlevel 1 set PYCMD=py -3
)
if not defined PYCMD (
    echo [ОШИБКА] Python не найден.
    echo Установите Python 3.11 или новее с сайта python.org
    echo и обязательно отметьте галочку "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

if not exist "ies_app.py" (
    echo [ОШИБКА] Файл ies_app.py не найден в этой папке.
    pause
    exit /b 1
)

echo [1/4] Установка нужных библиотек...
%PYCMD% -m pip install --upgrade pip
%PYCMD% -m pip install --upgrade openpyxl pyinstaller
if errorlevel 1 (
    echo [ОШИБКА] Не удалось установить библиотеки. Проверьте интернет.
    pause
    exit /b 1
)

echo.
echo [2/4] Очистка старой сборки...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "IES_Generator.spec" del /q "IES_Generator.spec"

echo.
echo [3/4] Сборка портативной папки...
%PYCMD% -m PyInstaller --onedir --windowed --clean --noconfirm ^
    --name IES_Generator ^
    --collect-all openpyxl ^
    ies_app.py
if errorlevel 1 (
    echo [ОШИБКА] Сборка не удалась. Скопируйте текст выше и покажите его.
    pause
    exit /b 1
)

echo.
echo [4/4] Готово.
echo.
echo Портативная версия лежит здесь:  %CD%\dist\IES_Generator\
echo Запускаемый файл внутри неё:      IES_Generator.exe
echo.
echo Заархивируйте всю папку IES_Generator целиком (не только .exe) —
echo программе нужны файлы рядом с ней. На другом компьютере: распаковать
echo и запустить IES_Generator.exe.
echo.
pause
