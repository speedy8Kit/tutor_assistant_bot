# CLAUDE.md

Инструкции для Claude Code при работе с этим репозиторием.

---

## Язык

Все планы, документация и общение с пользователем ведётся на **русском языке**.

---

## Обзор проекта

Telegram-бот для репетиторов: управление расписанием, данными учеников и напоминаниями.
Стек: Python 3.12, python-telegram-bot (async), PostgreSQL 15, Redis 7, Poetry, Docker.

---

## АБСОЛЮТНЫЕ ПРАВИЛА

Эти правила не обсуждаются и имеют приоритет над всеми остальными инструкциями.

1. **Никогда не запускать Python на хосте.** Запрещены `python`, `poetry run`, `pip install`, `poetry install` вне контейнера.
2. **Никогда не устанавливать пакеты вручную** внутри работающего контейнера. Все зависимости объявляются в `pyproject.toml` и устанавливаются через сборку Dockerfile.
3. **Никогда не изменять работающий контейнер** вместо редактирования исходников. Контейнер эфемерен — ручные изменения теряются при перезапуске.
4. **Всегда предполагать Docker-окружение.** Все команды должны использовать `docker-compose` или `docker exec`.
5. **Никогда не предлагать `pip install` или `apt install`** вне контекста Dockerfile.

Нарушение любого из правил делает окружение невоспроизводимым.

---

## Сервисы

| Сервис | Имя контейнера | Назначение |
|---|---|---|
| `dev` | `tutor-bot` | Интерактивная оболочка для разработки |
| `inference` | `tutor-bot-inference` | Запуск бота (`python -m tutor_assistant`) |
| `postgres` | `tutor-postgres` | База данных PostgreSQL 15 |
| `redis` | `tutor-redis` | Redis 7 — кэш / очередь задач |

Контейнер `dev` монтирует репозиторий в `/app` (изменения `.py`-файлов отражаются мгновенно — пересборка не нужна). Контейнер `inference` **не** монтирует репозиторий.

---

## Основные команды

### Запуск стека

```bash
# Запустить все сервисы (dev-оболочка + бот + postgres + redis)
docker-compose up -d

# Подключиться к dev-оболочке
docker exec -it tutor-bot bash
```

### Запуск бота (inference)

```bash
docker-compose up inference
```

### Разовая команда внутри контейнера

```bash
docker exec tutor-bot <команда>

# Примеры
docker exec tutor-bot python -m tutor_assistant
docker exec tutor-bot pytest
docker exec tutor-bot alembic upgrade head
```

### Пересборка образа

```bash
docker-compose build
# или для конкретного сервиса
docker-compose build dev
```

### Остановка и очистка

```bash
docker-compose down          # остановить контейнеры, сохранить volumes
docker-compose down -v       # остановить контейнеры + удалить volumes (деструктивно)
```

---

## Когда нужна пересборка

Пересобирать образ необходимо при изменении следующих файлов:

| Изменённый файл | Нужна пересборка |
|---|---|
| `Dockerfile` | Да — всегда |
| `pyproject.toml` | Да — изменился граф зависимостей |
| `poetry.lock` | Да — изменились закреплённые версии |
| `*.py` исходники | **Нет** — volume-монтирование отражает изменения сразу |
| `.env` / `ConfigDev.toml` | **Нет** — загружается в runtime |

**Команда пересборки:**
```bash
docker-compose build && docker-compose up -d
```

Claude должен явно сообщать пользователю о необходимости пересборки при изменении соответствующих файлов.

---

## Рабочий процесс разработки

```
Редактировать исходники → (пересборка если нужно) → exec команды в контейнере → наблюдать результат
```

1. Редактировать файлы на хосте в редакторе.
2. Если изменились `pyproject.toml`, `poetry.lock` или `Dockerfile` → пересборка.
3. Запускать команды через `docker exec tutor-bot <cmd>` или внутри подключённой оболочки.
4. Изменения в `src/` отражаются мгновенно через volume-монтирование.

---

## Управление зависимостями

Все зависимости управляются через Poetry внутри контейнера.

```bash
# Добавить зависимость (выполнять внутри контейнера)
docker exec tutor-bot poetry add <пакет>

# После добавления — закоммитить pyproject.toml и poetry.lock, затем пересобрать
docker-compose build
```

Никогда не запускать `poetry install` или `pip install` на хосте.

---

## Тестирование

Все тесты запускаются внутри контейнера.

```bash
# Запустить все тесты
docker exec tutor-bot pytest

# Запустить один тест
docker exec tutor-bot pytest tests/path/to/test_file.py::test_name

# Запустить с покрытием
docker exec tutor-bot pytest --cov=tutor_assistant
```

### Правила тестирования

- Использовать `pytest` как тест-раннер.
- Мокировать все внешние сервисы (Telegram API, PostgreSQL, Redis) — не зависеть от живых сервисов в юнит-тестах.
- Интеграционные тесты, требующие PostgreSQL или Redis, должны использовать сервисы из `docker-compose.yml` и запускаться внутри контейнера.
- Тестовые файлы находятся в `tests/` в корне репозитория.

---

## Линтинг и форматирование

Запускать внутри контейнера:

```bash
docker exec tutor-bot black src/ scripts/
docker exec tutor-bot isort src/ scripts/
docker exec tutor-bot ruff check src/ scripts/
docker exec tutor-bot mypy src/
```

Или за один проход через pre-commit (тоже внутри контейнера):

```bash
docker exec tutor-bot pre-commit run --all-files
```

---

## Миграции базы данных (Alembic)

```bash
# Применить все ожидающие миграции
docker exec tutor-bot alembic upgrade head

# Создать новую миграцию
docker exec tutor-bot alembic revision --autogenerate -m "описание"
```

---

## Переменные окружения

Объявляются в `.env` (скопировать из `.env.example`). Загружаются автоматически через `docker-compose`.

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен Telegram-бота |
| `DATABASE_URL` | `postgresql+asyncpg://abmine:abmine@postgres:5432/tutor_bot` |
| `REDIS_URL` | `redis://redis:6379/0` |
| `APP_CONFIG_FILE` | Путь к TOML-конфигу (по умолчанию: `ConfigDev.toml`) |

---

## Архитектура

```
src/tutor_assistant/
├── config.py        # AppConfig — TOML-конфиг, загружаемый через APP_CONFIG_FILE
├── bot.py           # TutorBot — сборка Application, подключение обработчиков
├── init_bot.py      # Низкоуровневая инициализация бота
├── database/        # SQLAlchemy async-модели + engine (в разработке)
├── handlers/        # Обработчики Telegram-обновлений (в разработке)
├── core/            # Бизнес-логика (в разработке)
├── utils/
│   └── logger.py    # get_logger() — JSON или текстовый логгер
└── __main__.py      # Точка входа
```

**Поток конфигурации:** `.env` → `AppConfig` (из TOML) → замороженные датаклассы (`BotConfigs`, `MainConfig`).

**Async:** Все обработчики и вызовы БД — async. Обработчики `telegram.ext.Application` должны быть `async def`.

---

## Антипаттерны — никогда так не делать

| Антипаттерн | Правильная альтернатива |
|---|---|
| `python script.py` на хосте | `docker exec tutor-bot python script.py` |
| `poetry install` на хосте | Объявить в `pyproject.toml`, пересобрать образ |
| `pip install <pkg>` где угодно | `docker exec tutor-bot poetry add <pkg>`, затем пересборка |
| `apt install` на хосте или в контейнере | Добавить в `Dockerfile`, пересобрать |
| Редактировать файлы внутри контейнера | Редактировать на хосте (volume-монтирование синхронизирует автоматически) |
| Запускать тесты на хосте | `docker exec tutor-bot pytest` |

---

## Правила ответов ассистента

При предложении команд или изменений Claude должен:

1. Всегда использовать `docker exec tutor-bot <cmd>` или `docker-compose` — никогда голые команды на хосте.
2. Явно писать "**Требуется пересборка:** `docker-compose build && docker-compose up -d`" при изменении `Dockerfile`, `pyproject.toml` или `poetry.lock`.
3. Никогда не предлагать `pip install`, `poetry install` или `apt install` вне контекста Dockerfile.
4. Предполагать, что контейнер `dev` (`tutor-bot`) запущен при предложении exec-команд.
5. При добавлении новой зависимости напоминать пользователю закоммитить `pyproject.toml` + `poetry.lock` и пересобрать.
