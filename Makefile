run-test-db:
	docker run --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=pass -d postgres