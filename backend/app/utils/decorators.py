"""Generic decorator utilities for dual async/sync mode support.

This module provides helper functions to create decorators that work seamlessly
with both async and sync functions, eliminating code duplication.
"""

import functools
import inspect
from typing import Any, Callable, TypeVar, ParamSpec

P = ParamSpec("P")
R = TypeVar("R")


def dual_mode_decorator(handler: Callable[[Callable, tuple, dict], Any]) -> Callable:
    """
    Create a decorator that works with both async and sync functions.

    This factory eliminates the need to write separate async_wrapper and
    sync_wrapper functions in every decorator.

    Args:
        handler: Function that implements the core decorator logic.
                 Receives (func, args, kwargs) and should call the function
                 and return its result, with any wrapping logic.

    Returns:
        A decorator function that automatically handles both async and sync modes

    Example:
        def my_decorator_logic(func, args, kwargs):
            print("Before")
            result = func(*args, **kwargs) if not inspect.iscoroutinefunction(func) else await func(*args, **kwargs)
            print("After")
            return result

        @dual_mode_decorator
        def my_decorator(func):
            return functools.partial(my_decorator_logic, func)
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                return await handler(func, args, kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
                return handler(func, args, kwargs)

            return sync_wrapper

    return decorator
