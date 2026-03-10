from typer.testing import CliRunner

import typer

from notion_cli._async import run_async

runner = CliRunner()

test_app = typer.Typer()


@test_app.command()
@run_async
async def hello() -> None:
    typer.echo("async works")


def test_async_command_runs() -> None:
    result = runner.invoke(test_app, [])
    assert result.exit_code == 0
    assert "async works" in result.output
