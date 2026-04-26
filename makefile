.PHONY: help up-dev up-inference tutor-bot down build logs shell cli test migrate clean test-bot stop-test-bot create-test-db logs-test

ID ?= 1

help:
	@echo "Доступные команды:"
	@echo "  make up-dev         - Запустить dev-окружение"
	@echo "  make up-inference   - Запустить бота (Telegram)"
	@echo "  make down           - Остановить все сервисы"
	@echo "  make build          - Пересобрать образы"
	@echo "  make logs           - Показать логи"
	@echo "  make bash           - Зайти в контейнер"
	@echo "  make cli            - Интерактивный CLI  (ID=<chat_id>)"
	@echo "  make test           - Запустить тесты"
	@echo "  make migrate        - Запустить миграции (prod)"
	@echo "  make clean          - Очистить всё"
	@echo "  make test-bot       - Запустить тестового бота (BOT_TOKEN_TEST)"
	@echo "  make stop-test-bot  - Остановить тестового бота"
	@echo "  make create-test-db - Создать тестовую БД (выполняется автоматически в test-bot)"
	@echo "  make logs-test      - Логи тестового бота"

up-dev:
	docker compose up -d dev

up-inference:
	docker compose up -d inference

tutor-bot:
	@if docker ps -q -f name=tutor-bot-inference | grep -q .; then \
		echo "Перезапускаю tutor-bot-inference..."; \
		docker compose restart inference; \
	else \
		echo "Запускаю tutor-bot-inference..."; \
		docker compose up -d inference; \
	fi

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f dev

bash:
	docker exec -it tutor-bot bash

cli:
	docker exec -it tutor-bot python -m tutor_assistant cli --tutor-id $(ID)

postgre:
	docker exec -it tutor-postgres psql -U abmine -d tutor_bot
	

test:
	docker exec tutor-bot pytest
	docker exec tutor-bot ruff format src/ tests/
	docker exec tutor-bot ruff check src/ tests/

migrate:
	docker compose --profile tools run --rm migrations

test-bot: create-test-db
	@if docker ps -q -f name=tutor-bot-test | grep -q .; then \
		echo "Перезапускаю tutor-bot-test..."; \
		docker compose --profile test restart inference-test; \
	else \
		echo "Запускаю tutor-bot-test..."; \
		docker compose --profile test up -d inference-test; \
	fi
	@echo "Логи: make logs-test"

stop-test-bot:
	docker compose --profile test stop inference-test

create-test-db:
	docker exec tutor-postgres psql -U abmine -d postgres -tc \
		"SELECT 1 FROM pg_database WHERE datname='tutor_bot_test'" \
		| grep -q 1 || \
		docker exec tutor-postgres psql -U abmine -d postgres -c \
		"CREATE DATABASE tutor_bot_test OWNER abmine;"

logs-test:
	docker compose --profile test logs -f inference-test

clean:
	docker compose down -v
	docker system prune -f