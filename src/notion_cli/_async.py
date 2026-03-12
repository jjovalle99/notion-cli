import asyncio
import functools
from collections.abc import Callable, Coroutine

import typer

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
        if timeout <= 0:
            coro.close()
            msg = f"Timeout must be positive, got {timeout}"
            raise ValueError(msg)
        return await asyncio.wait_for(coro, timeout=timeout)
    return await coro


async def paginate(
    method: Callable[..., Coroutine[object, object, dict[str, object]]],
    kwargs: dict[str, object],
    timeout: float | None,
    *,
    limit: int | None = None,
) -> tuple[list[object], dict[str, object]]:
    """Paginate a Notion API list method, collecting all results."""
    if limit is not None:
        kwargs["page_size"] = min(limit, 100)

    result = await await_with_timeout(method(**kwargs), timeout)
    all_results: list[object] = list(result.get("results") or [])

    while (
        result.get("has_more")
        and result.get("next_cursor")
        and result.get("results")
        and (limit is None or len(all_results) < limit)
    ):
        kwargs["start_cursor"] = result["next_cursor"]
        if limit is not None:
            kwargs["page_size"] = min(limit - len(all_results), 100)
        result = await await_with_timeout(method(**kwargs), timeout)
        all_results.extend(result.get("results") or [])

    envelope: dict[str, object] = {
        k: v for k, v in result.items() if k not in ("results", "has_more")
    }
    if limit is not None:
        all_results = all_results[:limit]
    return all_results, envelope


def run_async[**P](fn: Callable[P, Coroutine[object, object, None]]) -> Callable[P, None]:
    """Wrap an async function so Typer can call it synchronously."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        try:
            asyncio.run(fn(*args, **kwargs))
        except SystemExit:
            raise
        except TimeoutError:
            typer.echo(format_error("timeout", "API request timed out."), err=True)
            raise SystemExit(ExitCode.ERROR)
        except ValueError as exc:
            typer.echo(
                format_error("invalid_args", str(exc)),
                err=True,
            )
            raise SystemExit(ExitCode.BAD_ARGS)
        except Exception as exc:
            from notion_client.errors import APIResponseError, RequestTimeoutError

            if isinstance(exc, RequestTimeoutError):
                typer.echo(
                    format_error("timeout", str(exc), suggestion="Increase --timeout or retry."),
                    err=True,
                )
                raise SystemExit(ExitCode.ERROR)

            if isinstance(exc, APIResponseError):
                code_str = exc.code.value if hasattr(exc.code, "value") else str(exc.code)
                exit_code = _ERROR_CODE_MAP.get(code_str, ExitCode.ERROR)
                retry_after = exc.headers.get("retry-after")
                if retry_after and code_str == "rate_limited":
                    suggestion = f"Retry after {retry_after}s"
                else:
                    suggestion = f"HTTP {exc.status}"
                typer.echo(
                    format_error(code_str, str(exc), suggestion=suggestion),
                    err=True,
                )
                raise SystemExit(exit_code)

            typer.echo(
                format_error("unexpected", str(exc), suggestion=type(exc).__name__),
                err=True,
            )
            raise SystemExit(ExitCode.ERROR)

    return wrapper
