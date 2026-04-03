.PHONY: help up down build logs shell db test migrate clean

help:
	@echo "Доступные команды:"
	@echo "  make up      - Запустить все сервисы"
	@echo "  make down    - Остановить все сервисы"
	@echo "  make build   - Пересобрать образы"
	@echo "  make logs    - Показать логи бота"
	@echo "  make shell   - Зайти в контейнер бота"
	@echo "  make db      - Инициализировать БД"
	@echo "  make test    - Запустить тесты"
	@echo "  make migrate - Запустить миграции"
	@echo "  make clean   - Очистить всё"

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build --no-cache

logs:
	docker-compose logs -f bot

shell:
	docker-compose exec bot bash

db:
	docker-compose exec bot python scripts/init_db.py

test:
	docker-compose --profile tools run --rm tests

migrate:
	docker-compose --profile tools run --rm migrations

clean:
	docker-compose down -v
	docker system prune -f