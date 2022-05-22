from __future__ import annotations

from asyncio import iscoroutine
from datetime import timedelta
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Coroutine,
    Optional,
    Protocol,
    Sequence,
    TypeVar,
    Union,
)

from .cache import MemoryCache
from .proto import AsyncCache, Cache

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    P = ParamSpec("P")
else:
    P = TypeVar("P")
T = TypeVar("T")

UNSET = object()


def _extend_posargs(sig: list[int], posargs: list[int], *args: Any) -> None:
    for i in posargs:
        val = args[i]

        hashed = hash(val)

        sig.append(hashed)


def _extend_kwargs(sig: list[int], _kwargs: list[str], allow_unset: bool = False, **kwargs: Any) -> None:
    for name in _kwargs:
        try:
            val = kwargs[name]
        except KeyError:
            if allow_unset:
                continue

            raise

        hashed = hash(val)

        sig.append(hashed)


def _get_sig(
    func: Callable[..., Any],
    args: Any,
    kwargs: Any,
    include_posargs: Optional[list[int]] = None,
    include_kwargs: Optional[list[str]] = None,
    allow_unset: bool = False,
) -> Sequence[int]:
    signature: list[int] = [id(func)]

    if include_posargs is not None:
        _extend_posargs(signature, include_posargs, *args)
    else:
        for arg in args:
            signature.append(hash(arg))

    if include_kwargs is not None:
        _extend_kwargs(signature, include_kwargs, allow_unset, **kwargs)
    else:
        for name, value in kwargs.items():
            signature.append(hash((name, value)))

    return tuple(signature)


async def _maybe_async(value: Union[T, Coroutine[T, None, None]]) -> T:
    if iscoroutine(value):
        return await value
    return value  # type: ignore


class Cached(Protocol[P, T]):

    cache: Cache

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        ...


class AsyncCached(Cached[P, T]):
    async def __call__(self, *args: P.args, **kwargs: P.kwargs) -> "str":
        ...


def cached(
    timeout: Optional[Union[int, float, timedelta]] = None,
    include_posargs: Optional[list[int]] = None,
    include_kwargs: Optional[list[str]] = None,
    allow_unset: bool = False,
    cache: Optional[Cache] = None,
) -> Callable[[Callable[P, T]], Cached[P, T]]:
    _cache: Cache = cache or MemoryCache[Any, Any](timeout=timeout)

    def decorator(func: Callable[P, T]) -> Cached[P, T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            sig = _get_sig(func, args, kwargs, include_posargs, include_kwargs, allow_unset=allow_unset)

            try:
                return _cache[sig]
            except KeyError:
                pass

            result = func(*args, **kwargs)  # type: ignore

            _cache[sig] = result

            return result

        wrapper.cache = _cache

        return wrapper  # type: ignore

    return decorator


def async_cached(
    timeout: Optional[Union[int, float, timedelta]] = None,
    include_posargs: Optional[list[int]] = None,
    include_kwargs: Optional[list[str]] = None,
    allow_unset: bool = False,
    cache: Optional[Union[Cache, AsyncCache]] = None,
) -> Callable[[Callable[P, T]], AsyncCached[P, T]]:
    _cache: Union[Cache, AsyncCache] = cache or MemoryCache[Any, Any](timeout=timeout)

    def decorator(func: Callable[P, T]) -> AsyncCached[P, T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            sig = _get_sig(func, args, kwargs, include_posargs, include_kwargs, allow_unset=allow_unset)

            value = await _maybe_async(_cache.get(sig, UNSET))

            if value is not UNSET:
                return value

            result: T = await func(*args, **kwargs)  # type: ignore

            await _maybe_async(_cache.set(sig, result))

            return result

        wrapper.cache = _cache

        return wrapper  # type: ignore

    return decorator
