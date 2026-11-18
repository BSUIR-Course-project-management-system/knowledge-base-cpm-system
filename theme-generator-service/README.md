# Project Ideas Service

Локальный микросервис для генерации ровно 5 идей курсовых IT-проектов по предметной области.

## Состав
- FastAPI — HTTP API и Swagger.
- Ollama — локальный сервер языковой модели.
- Qwen3:4b — модель по умолчанию.
- Docker Compose — запускает API, Ollama и загрузчик модели.
- Docker Volume `ollama_data` — сохраняет модель между перезапусками.

Модель не встраивается в Docker-образ FastAPI: она хранится в volume контейнера Ollama и загружается один раз.

## Требования
- Docker Desktop (macOS/Windows) либо Docker Engine + Compose plugin (Linux).
- Интернет при первом запуске.
- Достаточно свободного места для образов и модели.
- Производительность зависит от CPU/RAM и возможностей компьютера.

## Запуск

1. Распакуйте проект.
2. Создайте `.env` из шаблона.

macOS/Linux:
```bash
cp .env.example .env
```

Windows PowerShell:
```powershell
Copy-Item .env.example .env
```

3. В корне проекта выполните:
```bash
docker compose up --build
```

При первом запуске Docker загрузит образы, поднимет Ollama, скачает модель из `LLM_MODEL`, затем запустит API. Первый запуск может занять время.

## Проверка
- Swagger: http://localhost:8000/docs
- API health: http://localhost:8000/health
- Готовность модели: http://localhost:8000/ready

В Swagger откройте `POST /generate`, нажмите **Try it out** и отправьте:
```json
{
  "subject_area": "Экология"
}
```

Ответ содержит `subject_area` и `ideas` — ровно 5 объектов с полями `title`, `description`, `goal`, `recommended_functionality`.

## Команды
Остановить:
```bash
docker compose down
```

Логи:
```bash
docker compose logs -f api
docker compose logs -f ollama
```

Состояние:
```bash
docker compose ps
```

Удалить в том числе скачанную модель:
```bash
docker compose down -v
```
Последняя команда удалит volume с моделью; при следующем запуске она скачается снова.

## Замена модели
В `.env` измените:
```env
LLM_MODEL=qwen3:8b
```
Затем пересоздайте шаг загрузки модели и API:
```bash
docker compose up -d --force-recreate model-init api
```
Более крупная модель требует больше ресурсов и может работать медленнее.

## Тесты без запуска Ollama
Создайте и активируйте виртуальное окружение, затем:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pytest
```

Активация окружения:
- macOS/Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`

## Примечания
- Порт опубликован только на `127.0.0.1`: API доступен локально на этом компьютере.
- `/health` проверяет API; `/ready` — доступность Ollama и наличие выбранной модели.
- Клиент возвращает только `message.content`, не поле `thinking`.
- Сейчас реализован провайдер Ollama; интерфейс `LLMClient` оставляет возможность добавить другие провайдеры.
- CPU-режим — наиболее универсальная отправная точка. GPU-ускорение на разных ОС требует отдельной настройки.
