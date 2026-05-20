FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e .

COPY mcp-searxng.py .

ENV SEARXNG_URL=http://172.17.0.1:2013

USER 1000

CMD ["python", "mcp-searxng.py", "-b", "0.0.0.0", "-p", "8000"]
