#!/bin/bash

echo "Создание виртуального окружения"
python3 -m venv .venv
echo "Виртуальное окружение успешно создано"

echo "Активация виртуального окружения"
source .venv/bin/activate
pip install --upgrade pip
echo "Виртуальное окружение активировано"

echo "Усатновка необходимых библиотек"
pip install -r requirements.txt
echo "Все необходимые библиотеки установлены"

echo "Инициализация модели"

python3 -c "
from sentence_transformers import SentenceTransformer
import os
path = 'models/all-MiniLM-L6-v2'
os.makedirs(path, exist_ok=True)
print('Скачивание весов')
model = SentenceTransformer('all-MiniLM-L6-v2')
model.save(path)
print('Модель сохранена в ' + path)
"

echo "Модель успешно установлена!"

