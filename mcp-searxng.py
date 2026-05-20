import json
import os
from typing import Any

import httpx
from attrs import define, field
from loguru import logger as log
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

SEARXNG_URL = os.environ.get('SEARXNG_URL', 'http://172.17.0.1:2013')
TIMEOUT = int(os.environ.get('HTTP_TIMEOUT', '15'))

mcp = FastMCP(
    'searxng-mcp',
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["*"],
        allowed_origins=["*"],
    )
)


@define
class HttpClient:
    timeout: int
    client: httpx.AsyncClient = field(default=None)

    def __attrs_post_init__(self) -> None:
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            limits=httpx.Limits(max_connections=50),
        )

    async def request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        body: str | dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if method.upper() not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
            raise ValueError(f'unsupported HTTP method: {method}')

        kwargs: dict[str, Any] = {'headers': headers}
        if params:
            kwargs['params'] = params
        if body is not None:
            if isinstance(body, str):
                kwargs['content'] = body
            else:
                kwargs['json'] = body

        r = await self.client.request(method.upper(), url, **kwargs)
        return {'status': r.status_code, 'headers': dict(r.headers), 'body': r.text}

    async def close(self) -> None:
        await self.client.aclose()


client = HttpClient(timeout=TIMEOUT)


@mcp.tool()
async def search(
    query: str,
    engines: list[str] | None = None,
    language: str | None = None,
    time_range: str | None = None,
    pages: int = 1,
) -> list[dict[str, Any]]:
    """Search the web using SearxNG.

    Args:
        query: Search query string.
        engines: List of SearxNG engines to use (e.g. ['google', 'duckduckgo']).
        language: Language code for results (e.g. 'en', 'de').
        time_range: Filter by time: day, month, or year.
        pages: Number of pages to fetch (default 1, max 10).
    """
    if not query or not query.strip():
        raise ValueError('query must not be empty')

    if pages < 1 or pages > 10:
        raise ValueError('pages must be between 1 and 10')

    base = f'{SEARXNG_URL.rstrip("/")}/search'
    all_results: list[dict[str, Any]] = []

    params: dict[str, Any] = {'q': query.strip(), 'format': 'json', 'pageno': 1}
    if engines:
        params['engines'] = ','.join(engines)
    if language:
        params['language'] = language
    if time_range:
        params['time_range'] = time_range

    for page in range(1, pages + 1):
        params['pageno'] = page
        log.info('searching page {page} for query: {q}', page=page, q=query)
        try:
            resp = await client.request('GET', base, params=params)
            data = json.loads(resp['body'])
        except httpx.HTTPStatusError as e:
            log.error('SearxNG HTTP error: {err}', err=e)
            break
        except httpx.RequestError as e:
            log.error('SearxNG connection error: {err}', err=e)
            break
        except json.JSONDecodeError as e:
            log.error('SearxNG invalid JSON: {err}', err=e)
            break

        all_results.extend(data.get('results', []))
        if not data.get('results') or page >= pages:
            break

    log.info('search returned {n} results', n=len(all_results))
    return all_results


@mcp.tool()
async def fetch_url(
    url: str,
    method: str = 'GET',
) -> dict[str, Any]:
    """Fetch a URL and return its content.

    Args:
        url: The URL to fetch.
        method: HTTP method to use (default GET).
    """
    url = url.strip()
    if not url:
        raise ValueError('url must not be empty')
    if not url.startswith(('http://', 'https://', 'http:', 'https:')):
        raise ValueError('url must start with http:// or https://')

    log.info('fetching: {u}', u=url)
    try:
        return await client.request(method.upper(), url)
    except httpx.RequestError as e:
        raise RuntimeError(f'failed to fetch URL: {e}') from e


@mcp.tool()
async def http_request(
    url: str,
    method: str = 'GET',
    headers: dict[str, str] | None = None,
    body: str | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make an HTTP request with full control over method, headers, and body.

    Args:
        url: The URL to request.
        method: HTTP method (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS).
        headers: Optional dict of HTTP headers.
        body: Optional request body as string or dict (auto-encoded as JSON if dict).
    """
    url = url.strip()
    if not url:
        raise ValueError('url must not be empty')
    if not url.startswith(('http://', 'https://', 'http:', 'https:')):
        raise ValueError('url must start with http:// or https://')

    log.info('http_request {m} {u}', m=method.upper(), u=url)
    try:
        return await client.request(method.upper(), url, headers=headers, body=body)
    except httpx.RequestError as e:
        raise RuntimeError(f'request failed: {e}') from e


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description='SearxNG MCP server (HTTP transport)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('-b', '--bind', default='127.0.0.1', help='host to bind')
    parser.add_argument('-p', '--port', type=int, default=8000, help='port to bind')
    args = parser.parse_args()

    log.info(
        'starting {name} on http://{host}:{port} (searxng={url}, timeout={t}s)',
        name=mcp.name,
        host=args.bind,
        port=args.port,
        url=SEARXNG_URL,
        t=TIMEOUT,
    )
    import uvicorn

    uvicorn.run(
        mcp.streamable_http_app(),
        host=args.bind,
        port=args.port,
        log_level='info',
    )


if __name__ == '__main__':
    main()
