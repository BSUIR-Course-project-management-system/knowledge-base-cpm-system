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

Для тестирования модуля использовалась библиотека **Pytest**, покрытие составило **94%**.

