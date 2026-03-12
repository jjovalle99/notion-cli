from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_client() -> Iterator[AsyncMock]:
    client = AsyncMock()
    # AsyncMock.__aenter__ returns a new AsyncMock by default, not `client` itself.
    # Commands use `async with AsyncClient(...) as client:` so __aenter__ must
    # return the same mock that has the method stubs (.pages, .blocks, etc.).
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    with patch("notion_client.AsyncClient", return_value=client):
        yield client
