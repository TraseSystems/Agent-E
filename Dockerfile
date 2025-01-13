FROM --platform=linux/amd64 python:3.11-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . /app
WORKDIR /app
RUN uv pip compile pyproject.toml -o requirements.txt
RUN uv pip install -r pyproject.toml --extra dev --system
RUN playwright install chrome
# RUN playwright install chromium
ENTRYPOINT ["uvicorn", "ae.server.api_routes:app", "--reload", "--loop", "asyncio", "--port", "8000", "--host", "0.0.0.0"]
