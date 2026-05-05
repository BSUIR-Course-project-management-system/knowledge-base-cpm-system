@echo off
setlocal

echo Создание виртуального окружения
python -m venv .venv
if %errorlevel% neq 0 (
    echo Ошибка при создании виртуального окружения. Убедитесь, что Python установлен.
    exit /b %errorlevel%
)
echo Виртуальное окружение успешно создано

echo Активация виртуального окружения
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
echo Виртуальное окружение активировано

echo Установка необходимых библиотек
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Ошибка при установке библиотек. Проверьте файл requirements.txt.
    exit /b %errorlevel%
)
echo Все необходимые библиотеки установлены

type nul > table_api\.env 2>nul
copy /Y table_api\.env.example table_api\.env >nul

mkdir table_api\secrets 2>nul
mkdir search_module\data 2>nul

echo Система поиска успешно установлена!
echo Система управления курсовыми и дипломными проектами готова к запуску!

endlocal