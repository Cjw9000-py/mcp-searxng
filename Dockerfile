FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY mcp-searxng.py .

ENV SEARXNG_URL=http://172.17.0.1:2013

USER 1000

CMD ["uv", "run", "python", "mcp-searxng.py"]
