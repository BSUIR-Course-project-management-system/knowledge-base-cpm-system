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

python3 -c "
from sentence_transformers import SentenceTransformer
import os
path = 'search_module/models/all-MiniLM-L6-v2'
os.makedirs(path, exist_ok=True)
print('Скачивание весов')
model = SentenceTransformer('all-MiniLM-L6-v2')
model.save(path)
print('Модель сохранена в ' + path)
"

touch table_api/.env

cp table_api/.env.example table_api/.env

mkdir table_api/secrets/


echo "Система поиска успешно установлена!"


echo "Система управления курсовыми и дипломными проектами готова к запуску!"
