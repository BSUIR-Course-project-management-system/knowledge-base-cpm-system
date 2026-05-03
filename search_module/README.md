# Search module 


## Описание:

Пользователь вводит запрос в строку поиска, далее следует запрос к модулю **table_api**, который возвращает список тем, после чего **search_module** с помощью технологии векторного поиска возвращает список наиболее релевантных тем модулю **recomendation_module**.

## Технологии:

* Python
* Pytest
* chromadb
* sentence-transformers

## Структура:
```
search_module/
    ├── .venv/
    ├── chroma_db/
    ├── models/
    ├── scripts/
    │   ├── setup.bat
    │   ├── setup.sh
    ├── src/
    │   ├── __init__.py
    │   ├── data_manager.py
    │   ├── loader.py
    │   ├── main.py
    │   ├── saver.py
    │   ├── settings.py
    │   ├── theme_finder_manager.py
    │   ├── theme_finder.py
    │   └── utils.py
    ├── tests/
    │   ├── json_tests/
    │   │   ├── test1.json
    │   │   └── test2.json
    │   ├── __init__.py
    │   ├── test_data_manager.py
    │   ├── test_loader.py
    │   ├── test_saver.py
    │   └── test_theme_finder_manager.py
    ├── __init__.py
    ├── data.json
    ├── README.md
    └── requirements.txt
```

## Тестирование 

Для тестирования модуля использовалась библиотека **Pytest**, покрытие составило **97%**.


## Установка

Для установки необходимых зависимостей полсе клонирования репозитория необходимо запустить файл установки. Для пользователей системы Linux/macOS  - это файл **setup.sh**, а для пользователей **Windows** - **setup.bat**.

После установки всех зависимостей и активации виртуального окружения (*source .venv/bin/activate*, находясь в модуле search_module), находясь в папке **knowledge-base-cpm-system**, нужно выполнить:

* **Windows**

```python
python -m search_module.src.main
```

* **Linux/macOS**

```python3
python3 -m search_module.src.main
``` 

