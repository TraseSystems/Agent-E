PORT=8001

run-basic:
	python -u -m ae.main

run-api:
	uvicorn ae.server.api_routes:app --reload --loop asyncio --port 8001

ping-api:
	curl -s --location 'http://127.0.0.1:${PORT}/execute_task' \
	--header 'Content-Type: application/json' \
	--data '{
		"command": "In April of 1977, who was the Prime Minister of the first place mentioned by name in the Book of Esther (in the New International Version)?"
	}'

ping-api-tools:
	python -c "PORT=${PORT}; import requests, json; print(json.dumps(requests.get(f'http://127.0.0.1:{PORT}/list-tools', headers={'Content-Type': 'application/json'}).json(), indent=2))"

build:
	docker build . -t agent-e:local

run-docker:
	docker run --platform linux/amd64 \
		-p 8001:8000 \
		-it agent-e:local

