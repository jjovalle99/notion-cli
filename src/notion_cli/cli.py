import importlib

import click
import typer
import typer.core as tc
import typer.main as tm
from typer.models import CommandInfo

_LAZY_GROUPS: dict[str, tuple[str, str]] = {
    "page": ("notion_cli.commands.page", "page_app"),
    "db": ("notion_cli.commands.db", "db_app"),
    "block": ("notion_cli.commands.block", "block_app"),
    "comment": ("notion_cli.commands.comment", "comment_app"),
    "user": ("notion_cli.commands.user", "user_app"),
    "team": ("notion_cli.commands.team", "team_app"),
    "auth": ("notion_cli.commands.auth", "auth_app"),
}

_LAZY_COMMANDS: dict[str, tuple[str, str]] = {
    "search": ("notion_cli.commands.search", "search"),
    "schema": ("notion_cli.commands.schema", "schema"),
    "api": ("notion_cli.commands.api", "api"),
}

_LAZY_ALL = {**_LAZY_GROUPS, **_LAZY_COMMANDS}


class _LazyTyperGroup(tc.TyperGroup):
    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name in _LAZY_GROUPS:
            mod_path, attr = _LAZY_GROUPS[cmd_name]
            typer_app = getattr(importlib.import_module(mod_path), attr)
            group = tm.get_group(typer_app)
            group.name = cmd_name
            return group
        if cmd_name in _LAZY_COMMANDS:
            mod_path, attr = _LAZY_COMMANDS[cmd_name]
            callback = getattr(importlib.import_module(mod_path), attr)
            info = CommandInfo(callback=callback, name=cmd_name)
            return tm.get_command_from_info(
                info,
                pretty_exceptions_short=True,
                rich_markup_mode=self.rich_markup_mode,
            )
        return super().get_command(ctx, cmd_name)

    def list_commands(self, ctx: click.Context) -> list[str]:
        return list(_LAZY_ALL)

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except click.UsageError as e:
            if self.suggest_commands:
                from difflib import get_close_matches

                matches = get_close_matches(args[0], _LAZY_ALL) if args else []
                if matches:
                    suggestions = ", ".join(f"{m!r}" for m in matches)
                    message = e.message.rstrip(".")
                    e.message = f"{message}. Did you mean {suggestions}?"
            raise


app = typer.Typer(
    name="notion",
    cls=_LazyTyperGroup,
    help=(
        "Agent-friendly CLI for the Notion API.\n\n"
        "Every command outputs compact JSON to stdout by default. "
        "Errors are written as JSON to stderr.\n\n"
        "Authentication: run 'notion auth login', set NOTION_API_KEY env var, "
        "or pass --token on any command."
    ),
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        from notion_cli import __version__

        typer.echo(f"notion-cli {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Print version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    pass
