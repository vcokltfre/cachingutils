from datetime import timedelta
from json import dumps, loads
from pickle import dumps, loads
from typing import Any, Generic, Optional, Protocol, Type, TypeVar, Union, overload

from redis import Redis
from redis.asyncio import Redis as AsyncRedis  # type: ignore

JSON = Union[dict[str, Any], list[Any], str, int, float, bool, None]

_Sessions: dict[str, "RedisCache[Any, Any]"] = {}
_AsyncSessions: dict[str, "AsyncRedisCache[Any, Any]"] = {}


class RedisKey(Protocol):
    def __str__(self) -> str:
        ...


class RedisCachable(Protocol):
    def __str__(self) -> str:
        ...

    @staticmethod
    def __fromstr__(value: str) -> "RedisCachable":
        ...


KT = TypeVar("KT", bound=RedisKey)
VT = TypeVar("VT", bound=Union[RedisCachable, JSON])


class _AsyncRedis(Protocol):
    async def get(self, key: Any, default: Optional[Any] = None) -> Optional[Any]:
        ...

    async def set(self, key: Any, value: Any, ex: Optional[timedelta] = None) -> None:
        ...

    async def exists(self, key: Any) -> bool:
        ...


class RedisCache(Generic[KT, VT]):
    def __init__(
        self,
        type: Optional[Type[VT]] = None,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        items: Optional[dict[KT, VT]] = None,
        timeout: Optional[float] = None,
        prefix: Optional[str] = None,
        session: Optional[Redis] = None,  # type: ignore
        redis_options: Optional[dict[Any, Any]] = None,
    ) -> None:
        self._type = type
        self._redis: Redis[str] = session or Redis(host=host, port=port, db=db, **(redis_options or {}))
        self._timeout: Optional[timedelta] = timedelta(seconds=timeout) if timeout else None
        self._prefix: str = prefix or ""

        self._json = not hasattr(self._type, "__fromstr__")

        if items:
            for key, value in items.items():
                self.set(key, value)

    def __getitem__(self, key: KT) -> VT:
        value = self.get(key)

        if key not in self:
            raise KeyError(key)

        return value  # type: ignore

    def __setitem__(self, key: KT, value: VT) -> None:
        self._redis.set(self._prefix + str(key), str(value), ex=self._timeout)

    def __contains__(self, key: Any) -> bool:
        return bool(self._redis.exists(self._prefix + str(key)))

    @overload
    def get(self, key: KT, default: VT) -> VT:
        ...

    @overload
    def get(self, key: KT, default: None = None) -> Optional[VT]:
        ...

    def get(self, key: KT, default: Optional[VT] = None) -> Optional[VT]:
        value = self._redis.get(self._prefix + str(key))

        if key not in self:
            return default

        if self._json:
            return loads(value)  # type: ignore

        return self._type.__fromstr__(value.decode())  # type: ignore

    def set(self, key: Any, value: Any, timeout: Optional[float] = None) -> None:
        _timeout = timedelta(seconds=timeout) if timeout else self._timeout

        if self._json:
            self._redis.set(self._prefix + str(key), dumps(value), ex=_timeout)
            return

        self._redis.set(self._prefix + str(key), str(value), ex=_timeout)


class AsyncRedisCache(Generic[KT, VT]):
    def __init__(
        self,
        type: Optional[Type[VT]] = None,
        host: str = "127.0.0.1",
        port: int = 6379,
        db: int = 0,
        timeout: Optional[float] = None,
        prefix: Optional[str] = None,
        session: Optional[AsyncRedis] = None,
        redis_options: Optional[dict[Any, Any]] = None,
    ) -> None:
        self._type = type
        self._redis: _AsyncRedis = session or AsyncRedis.from_url(f"redis://{host}:{port}/{db}", **(redis_options or {}))  # type: ignore
        self._timeout: Optional[timedelta] = timedelta(seconds=timeout) if timeout else None
        self._prefix: str = prefix or ""

        self._json = not hasattr(self._type, "__fromstr__")

    @overload
    async def get(self, key: KT, default: VT) -> VT:
        ...

    @overload
    async def get(self, key: KT, default: None = None) -> Optional[VT]:
        ...

    async def get(self, key: KT, default: Optional[VT] = None) -> Optional[VT]:
        value = await self._redis.get(self._prefix + str(key))
        exists = await self._redis.exists(self._prefix + str(key))

        if not exists:
            return default

        if self._json:
            return loads(value)  # type: ignore

        return self._type.__fromstr__(value.decode())  # type: ignore

    async def set(self, key: Any, value: Any, timeout: Optional[float] = None) -> None:
        _timeout = timedelta(seconds=timeout) if timeout else self._timeout

        if self._json:
            await self._redis.set(self._prefix + str(key), dumps(value), ex=_timeout)
            return

        await self._redis.set(self._prefix + str(key), str(value), ex=_timeout)


def session(
    name: str,
    type: Optional[Type[VT]] = None,
    host: str = "127.0.0.1",
    port: int = 6379,
    db: int = 0,
    items: Optional[dict[KT, VT]] = None,
    timeout: Optional[float] = None,
    prefix: Optional[str] = None,
    session: Optional["Redis[Any]"] = None,  # type: ignore
    redis_options: Optional[dict[Any, Any]] = None,
) -> RedisCache[Any, VT]:
    if name not in _Sessions:
        _Sessions[name] = RedisCache(
            type=type,
            host=host,
            port=port,
            db=db,
            items=items,
            timeout=timeout,
            prefix=prefix,
            session=session,
            redis_options=redis_options,
        )

    return _Sessions[name]


def async_session(
    name: str,
    type: Optional[Type[VT]] = None,
    host: str = "127.0.0.1",
    port: int = 6379,
    db: int = 0,
    timeout: Optional[float] = None,
    prefix: Optional[str] = None,
    session: Optional[AsyncRedis] = None,
    redis_options: Optional[dict[Any, Any]] = None,
) -> AsyncRedisCache[Any, VT]:
    if name not in _AsyncSessions:
        _AsyncSessions[name] = AsyncRedisCache(
            type=type,
            host=host,
            port=port,
            db=db,
            timeout=timeout,
            prefix=prefix,
            session=session,
            redis_options=redis_options,
        )

    return _AsyncSessions[name]
