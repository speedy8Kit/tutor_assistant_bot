.PHONY: help up-dev up-inference down build logs shell cli test migrate clean

ID ?= 1

help:
	@echo "Доступные команды:"
	@echo "  make up-dev       - Запустить dev-окружение"
	@echo "  make up-inference - Запустить бота (Telegram)"
	@echo "  make down         - Остановить все сервисы"
	@echo "  make build        - Пересобрать образы"
	@echo "  make logs         - Показать логи"
	@echo "  make bash         - Зайти в контейнер"
	@echo "  make cli          - Интерактивный CLI  (ID=<chat_id>)"
	@echo "  make test         - Запустить тесты"
	@echo "  make migrate      - Запустить миграции"
	@echo "  make clean        - Очистить всё"

up-dev:
	docker compose up -d dev

up-inference:
	docker compose up -d inference

down:
	docker compose down

build:
	docker compose build --no-cache

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

clean:
	docker compose down -v
	docker system prune -f