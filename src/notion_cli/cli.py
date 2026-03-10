import typer

app = typer.Typer(
    name="notion",
    help=(
        "Agent-friendly CLI for the Notion API.\n\n"
        "Every command outputs JSON to stdout by default. "
        "Use --human for rich-formatted human-readable output. "
        "Errors are written as JSON to stderr.\n\n"
        "Authentication: set NOTION_API_KEY environment variable "
        "or pass --token on any command."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
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


from notion_cli.commands.block import block_app  # noqa: E402
from notion_cli.commands.comment import comment_app  # noqa: E402
from notion_cli.commands.db import db_app  # noqa: E402
from notion_cli.commands.page import page_app  # noqa: E402
from notion_cli.commands.search import search  # noqa: E402
from notion_cli.commands.team import team_app  # noqa: E402
from notion_cli.commands.user import user_app  # noqa: E402

app.command(
    name="search",
    help=(
        "Search the Notion workspace by title.\n\n"
        "Returns pages and databases matching the query, ordered by relevance. "
        "Only content shared with the integration is searchable.\n\n"
        "Examples:\n\n"
        "  notion search 'meeting notes'\n\n"
        "  notion search 'Q1 roadmap' --type page\n\n"
        "  notion search 'projects' --type database"
    ),
)(search)
app.add_typer(page_app)
app.add_typer(db_app)
app.add_typer(block_app)
app.add_typer(comment_app)
app.add_typer(user_app)
app.add_typer(team_app)
