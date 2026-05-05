@echo off

echo Создание виртуального окружения
python -m venv .venv
if %errorlevel% neq 0 (
    echo Ошибка при создании виртуального окружения.
    exit /b %errorlevel%
)
echo Виртуальное окружение успешно создано.

echo Активация виртуального окружения
call .venv\Scripts\activate
python -m pip install --upgrade pip
echo Виртуальное окружение активировано.

echo Установка необходимых библиотек
pip install -r requirements.txt
echo Все необходимые библиотеки установлены.

echo Установка системы поиска.

python -c "from sentence_transformers import SentenceTransformer; import os; path = os.path.join('search_module', 'models', 'all-MiniLM-L6-v2'); os.makedirs(path, exist_ok=True); print('Скачивание весов'); model = SentenceTransformer('all-MiniLM-L6-v2'); model.save(path); print('Модель сохранена в ' + path)"

if not exist "table_api\.env" type nul > "table_api\.env"

copy "table_api\.env.example" "table_api\.env" /Y

if not exist "table_api\secrets\" mkdir "table_api\secrets\"
if not exist "search_module\data\" mkdir "search_module\data\"

echo Система поиска успешно установлена!
echo Система управления курсовыми и дипломными проектами готова к запуску!

pause