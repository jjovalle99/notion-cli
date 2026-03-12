from typing import Annotated

import click
import typer
import typer.main as tm

from notion_cli.output import ExitCode, format_error, format_json


def _param_schema(param: click.Parameter) -> dict[str, object]:
    result: dict[str, object] = {"name": param.name or ""}
    if isinstance(param, click.Argument):
        result["kind"] = "argument"
    else:
        result["kind"] = "option"
        if isinstance(param, click.Option) and param.opts:
            result["flags"] = param.opts
    result["required"] = param.required
    if param.default is not None:
        result["default"] = param.default
    if isinstance(param.type, click.Choice):
        result["choices"] = list(param.type.choices)
    result["type"] = param.type.name
    if isinstance(param, click.Option) and param.help:
        result["help"] = param.help
    return result


def _command_schema(cmd: click.Command, name: str) -> dict[str, object]:
    params = [_param_schema(p) for p in cmd.params if p.name != "help"]
    return {
        "command": name,
        "description": (cmd.help or "").split("\n")[0].strip(),
        "parameters": params,
    }


def _resolve_command(
    group: click.Group, parts: list[str], ctx: click.Context
) -> tuple[click.Command | None, str]:
    """Walk the command tree to resolve a space-separated path."""
    name_parts: list[str] = []
    current: click.Command = group
    for part in parts:
        if not isinstance(current, click.Group):
            return None, " ".join(name_parts)
        resolved = current.get_command(ctx, part)
        if resolved is None:
            return None, " ".join([*name_parts, part])
        name_parts.append(part)
        current = resolved
    return current, " ".join(name_parts)


def schema(
    command_path: Annotated[
        list[str],
        typer.Argument(help="Command path to introspect. Example: 'page create' or 'search'."),
    ],
) -> None:
    """Show the JSON schema of a command's parameters.

    Outputs a machine-readable description of the command's arguments,
    options, types, defaults, and help text. Useful for agents to
    discover what a command accepts without parsing --help.

    Examples:
        notion schema page create
        notion schema db query
        notion schema search
    """
    from notion_cli.cli import app

    click_app = tm.get_group(app)
    ctx = click.Context(click_app)
    cmd, name = _resolve_command(click_app, command_path, ctx)
    if cmd is None or isinstance(cmd, click.Group):
        typer.echo(
            format_error("unknown_command", f"Command not found: {' '.join(command_path)}"),
            err=True,
        )
        raise SystemExit(ExitCode.BAD_ARGS)

    typer.echo(format_json(_command_schema(cmd, name)))
