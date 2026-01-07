.PHONY: up down logs restart clean db-migrate db-reset install

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

clean:
	docker-compose down -v
	rm -rf storage/*

db-migrate:
	docker-compose exec api alembic upgrade head

db-reset:
	docker-compose down -v
	docker-compose up -d postgres redis
	sleep 5
	docker-compose up -d api
	sleep 5
	$(MAKE) db-migrate

install:
	cd apps/web && npm install

build:
	docker-compose build

shell-api:
	docker-compose exec api bash

shell-worker:
	docker-compose exec worker bash

shell-db:
	docker-compose exec postgres psql -U postgres -d kommo_call_analyzer

test-api:
	docker-compose exec api pytest

create-migration:
	docker-compose exec api alembic revision --autogenerate -m "$(msg)"








