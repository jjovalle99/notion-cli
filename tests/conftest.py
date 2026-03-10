from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def mock_client() -> AsyncIterator[AsyncMock]:
    client = AsyncMock()
    with patch("notion_client.AsyncClient", return_value=client):
        yield client
