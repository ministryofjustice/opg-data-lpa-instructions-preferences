up:
	docker compose up --build --remove-orphans -d

down:
	docker compose down

test:
	docker compose up unit-tests-request-handler
	docker compose up unit-tests-processor

integration-test: up
	(cd integration; python -m pytest .)
