import asyncio
import functools
from collections.abc import Callable, Coroutine


def run_async[**P](fn: Callable[P, Coroutine[object, object, None]]) -> Callable[P, None]:
    """Wrap an async function so Typer can call it synchronously."""

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> None:
        asyncio.run(fn(*args, **kwargs))

    return wrapper
