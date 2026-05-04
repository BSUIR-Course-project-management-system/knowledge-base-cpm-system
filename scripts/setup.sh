#!/bin/bash

echo "Создание виртуального окружения"
python3 -m venv .venv
echo "Виртуальное окружение успешно создано"

echo "Активация виртуального окружения"
source .venv/bin/activate
pip install --upgrade pip
echo "Виртуальное окружение активировано"

echo "Установка необходимых библиотек"
pip install -r requirements.txt
echo "Все необходимые библиотеки установлены"

echo "Установка ситемы поиска"

chmod +x search_module/scripts/setup.sh

./search_module/scripts/setup.sh

touch table_api/.env

table_api/.env.example > table_api/.env


echo "Система поиска успешно установлена!"


echo "Система управления курсовыми и дипломными проектами готова к запуску!"
