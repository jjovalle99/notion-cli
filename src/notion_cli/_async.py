import asyncio
import functools
from collections.abc import Callable, Coroutine

from notion_cli.output import ExitCode, format_error

_ERROR_CODE_MAP: dict[str, ExitCode] = {
    "object_not_found": ExitCode.NOT_FOUND,
    "unauthorized": ExitCode.PERMISSION,
    "restricted_resource": ExitCode.PERMISSION,
    "rate_limited": ExitCode.RATE_LIMITED,
}


async def await_with_timeout[T](coro: Coroutine[object, object, T], timeout: float | None) -> T:
    """Await a coroutine with an optional timeout."""
    if timeout is not None:
        return await asyncio.wait_for(coro, timeout=timeout)
    return await coro


def run_async[**P](fn: Callable[P, Coroutine[object, object, None]]) -> Callable[P, None]:
    """Wrap an async function so Typer can call it synchronously."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            asyncio.run(fn(*args, **kwargs))
        except SystemExit:
            raise
        except TimeoutError:
            import typer

            typer.echo(format_error("timeout", "API request timed out."), err=True)
            raise SystemExit(ExitCode.ERROR)
        except Exception as exc:
            import typer

            from notion_client.errors import APIResponseError

            if isinstance(exc, APIResponseError):
                exit_code = _ERROR_CODE_MAP.get(exc.code, ExitCode.ERROR)
                typer.echo(
                    format_error(exc.code, str(exc), suggestion=f"HTTP {exc.status}"),
                    err=True,
                )
                raise SystemExit(exit_code)

            typer.echo(
                format_error("unexpected", str(exc), suggestion=type(exc).__name__),
                err=True,
            )
            raise SystemExit(ExitCode.ERROR)

    return wrapper
