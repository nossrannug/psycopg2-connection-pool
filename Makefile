run-test-db:
	docker run --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=pass -d postgres

test-integration:
	pytest tests/integration

test-unit:
	pytest tests/unit

.PHONY: test
test:
	pytest