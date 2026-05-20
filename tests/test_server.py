import importlib
import os
import sys
from pathlib import Path

import pytest

_here = Path(__file__).resolve().parent
_script = _here.parent / 'mcp-searxng.py'

_spec = importlib.util.spec_from_file_location('mcp_searxng_script', _script)
_m = importlib.util.module_from_spec(_spec)
sys.modules['mcp_searxng_script'] = _m
_spec.loader.exec_module(_m)

search = _m.search
fetch_url = _m.fetch_url
http_request = _m.http_request


@pytest.fixture(autouse=True)
def _clear_searxng_env() -> None:
    """Ensure tests always hit the SearxNG URL set at import time, not overridden."""
    yield


@pytest.mark.asyncio
async def test_search_empty_query() -> None:
    with pytest.raises(ValueError, match='query must not be empty'):
        await search(query='')


@pytest.mark.asyncio
async def test_search_empty_whitespace() -> None:
    with pytest.raises(ValueError, match='query must not be empty'):
        await search(query='   ')


@pytest.mark.asyncio
async def test_search_invalid_pages() -> None:
    with pytest.raises(ValueError, match='pages must be between 1 and 10'):
        await search(query='test', pages=0)

    with pytest.raises(ValueError, match='pages must be between 1 and 10'):
        await search(query='test', pages=11)


@pytest.mark.asyncio
async def test_fetch_url_empty() -> None:
    with pytest.raises(ValueError, match='url must not be empty'):
        await fetch_url(url='')


@pytest.mark.asyncio
async def test_fetch_url_no_protocol() -> None:
    with pytest.raises(ValueError, match='url must start with'):
        await fetch_url(url='not a url')


@pytest.mark.asyncio
async def test_http_request_empty_url() -> None:
    with pytest.raises(ValueError, match='url must not be empty'):
        await http_request(url='')


@pytest.mark.asyncio
async def test_http_request_no_protocol() -> None:
    with pytest.raises(ValueError, match='url must start with'):
        await http_request(url='not a url')


@pytest.mark.asyncio
async def test_http_request_unsupported_method() -> None:
    with pytest.raises(ValueError, match='unsupported HTTP method'):
        await http_request(url='http://example.com', method='INVALID')
