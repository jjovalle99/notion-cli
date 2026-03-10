import asyncio
from unittest.mock import AsyncMock

from typer.testing import CliRunner

from notion_cli.cli import app


def test_command_times_out_on_hung_api(runner: CliRunner, mock_client: AsyncMock) -> None:
    async def hang(*args: object, **kwargs: object) -> None:
        await asyncio.sleep(999)

    mock_client.search.side_effect = hang

    result = runner.invoke(
        app, ["search", "test", "--timeout", "0.1"], env={"NOTION_API_KEY": "secret"}
    )

    assert result.exit_code == 1
    assert "timeout" in result.output.lower()


def test_negative_timeout_gives_error(runner: CliRunner, mock_client: AsyncMock) -> None:
    result = runner.invoke(
        app, ["search", "test", "--timeout", "-1"], env={"NOTION_API_KEY": "secret"}
    )

    assert result.exit_code == 1
    assert "must be positive" in result.output.lower() or "unexpected" in result.output.lower()


def test_zero_timeout_gives_error(runner: CliRunner, mock_client: AsyncMock) -> None:
    result = runner.invoke(
        app, ["search", "test", "--timeout", "0"], env={"NOTION_API_KEY": "secret"}
    )

    assert result.exit_code == 1
