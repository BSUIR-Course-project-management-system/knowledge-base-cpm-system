<h1 align="center">knowledge-base-cpm-system</h1>

[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
[![Rich](https://img.shields.io/badge/Rich-CLI-purple)](https://rich.readthedocs.io/)
[![Questionary](https://img.shields.io/pypi/v/questionary?label=questionary&color=blue&logo=python)](https://pypi.org/project/questionary/)

![Google Sheets](https://img.shields.io/badge/Google%20Sheets-34A853?style=for-the-badge&logo=google-sheets&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)
![Pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Gspread](https://img.shields.io/badge/Gspread-4285F4?style=for-the-badge&logo=python&logoColor=white)
![Chroma](https://img.shields.io/badge/ChromaDB-FFA500?style=for-the-badge&logoColor=white)
![Sentence Transformers](https://img.shields.io/badge/Sentence%20Transformers-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)

## Описание:

Cистема для хранения историй курсовых/дипломных проектов, тем, руководителей, требований, а также для поддержки подбора тем и контроля статуса работ.


## Установка 


Для установки системы локально на устройство, необходимо клонировать репозиторий командой 

```bash
git clone https://github.com/BSUIR-Course-project-management-system/knowledge-base-cpm-system.git
```

После клонировнаия проекта нужно перейти в корневую папку, для этого необходимо выполнить команду

```bash
cd knowledge-base-cpm-system/
```

Далее нужно запустить скрипт установки.

* Linux/macOS

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

* Windows

```bat
.\scripts\setup.bat
```

После успешной установки всех необходимых библиотек и зависимостей необходимо получить свой файл авторизации **credentials.json**  и поместить его в папку **table_api/secrets/**. Также нужно получить **id папки на google disk** и изменить его в **.env**.

Далее необходимо активировать виртуальное окружение командой

* Linux/macOS

```bash
source .venv/bin/activate
```

* Windows

```bat
.\.venv\Scripts\activate
```

Теперь все готово к первому запуску!

* Linux/macOS

```bash
python3 -m interface.main
```
* Windows
```bat
python -m interface.main
```

## Тестирование

Для тестирования программы использовалась библиотека **Pytest**. Для запуска тестов необходимо в терминале выполнить команду (в предварительно активированном виртуальном окружении).

* Linux/macOS/Windows

```python
pytest
```

## Авторы

*  GitHub: [@Artemdjdj](https://github.com/Artemdjdj), [@Frostnout](https://github.com/dBurbas), [@Aratakrr1](https://github.com/suyeatolog), [@Gen1us02](https://github.com/Gen1us02)


## Лицензия

Данный проект распространяется по лицензии в соответствии с [MIT License](https://opensource.org/license/mit/)