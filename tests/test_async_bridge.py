import typer
from typer.testing import CliRunner

from notion_cli._async import run_async

_app = typer.Typer()


@_app.command()
@run_async
async def hello() -> None:
    typer.echo("async works")


def test_async_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(_app, [])
    assert result.exit_code == 0
    assert "async works" in result.output
