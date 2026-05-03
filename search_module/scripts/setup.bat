@echo off
chcp 65001 >nul


echo Создание виртуального окружения
python -m venv .venv
if %errorlevel% neq 0 (
    echo Ошибка при создании виртуального окружения. Проверьте, установлен ли Python.
    pause
    exit /b
)
echo Виртуальное окружение успешно создано

echo Активация виртуального окружения
call .venv\Scripts\activate
python -m pip install --upgrade pip
echo Виртуальное окружение активировано

echo Установка необходимых библиотек
pip install -r requirements.txt
echo Все необходимые библиотеки установлены

echo Инициализация модели
python -c "from sentence_transformers import SentenceTransformer; import os; path = 'models/all-MiniLM-L6-v2'; os.makedirs(path, exist_ok=True); print('Скачивание весов'); model = SentenceTransformer('all-MiniLM-L6-v2'); model.save(path); print('Модель сохранена в ' + path)"

echo Модель успешно установлена!
pause