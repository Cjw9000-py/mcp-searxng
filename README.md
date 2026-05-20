# searxng-mcp

MCP server for web search and HTTP requests via SearxNG.

## Tools

- **search** — Query SearxNG for web search results
- **fetch_url** — Fetch a URL and return its content
- **http_request** — Full HTTP control: method, headers, body

## Setup

```bash
uv sync
uv run pytest
```

## Run

```bash
uv run python -m mcp_searxng
```

## Configuration

| Env var | Default | Description |
| --- | --- | --- |
| `SEARXNG_URL` | `http://172.19.0.1:2013` | SearxNG instance URL |
| `HTTP_TIMEOUT` | `15` | HTTP request timeout in seconds |
