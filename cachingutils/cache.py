from datetime import timedelta
from time import time
from typing import Generic, Optional, TypeVar, Union, overload

from lru import LRU  # type: ignore

KT = TypeVar("KT")
VT = TypeVar("VT")


class _Expirable(Generic[KT]):
    __slots__ = (
        "value",
        "_expires",
    )

    def __init__(self, value: KT, timeout: Optional[float] = None) -> None:
        self.value = value
        self._expires = time() + timeout if timeout is not None else None

    @property
    def expired(self) -> bool:
        return self._expires is not None and time() > self._expires


class MemoryCache(Generic[KT, VT]):
    __slots__ = (
        "_items",
        "_timeout",
    )

    def __init__(
        self,
        items: Optional[dict[KT, VT]] = None,
        timeout: Optional[Union[float, int, timedelta]] = None,
    ) -> None:
        if isinstance(timeout, timedelta):
            timeout = timeout.total_seconds()

        self._items: dict[KT, _Expirable[VT]] = {
            key: _Expirable(value, timeout) for key, value in (items or {}).items() if value
        }
        self._timeout: Optional[Union[float, int]] = timeout

    def __getitem__(self, key: KT) -> VT:
        item = self._items[key]

        if item.expired:
            del self._items[key]
            raise KeyError(key)

        return item.value

    def __setitem__(self, key: KT, value: VT) -> None:
        self._items[key] = _Expirable(value, self._timeout)

    def __delitem__(self, key: KT) -> None:
        del self._items[key]

    def __contains__(self, key: KT) -> bool:
        return key in self._items and not self._items[key].expired

    @overload
    def get(self, key: KT, default: VT) -> VT:
        ...

    @overload
    def get(self, key: KT, default: None = None) -> Optional[VT]:
        ...

    def get(self, key: KT, default: Optional[VT] = None) -> Optional[VT]:
        try:
            return self[key]
        except KeyError:
            return default or None

    def set(self, key: KT, value: VT, timeout: Optional[Union[float, int, timedelta]] = None) -> None:
        if isinstance(timeout, timedelta):
            timeout = timeout.total_seconds()
        self._items[key] = _Expirable(value, timeout or self._timeout)

    def purge(self) -> int:
        purged = 0

        for key, value in self._items.items():
            if value.expired:
                del self._items[key]
                purged += 1

        return purged


class LRUMemoryCache(MemoryCache[KT, VT]):
    def __init__(
        self,
        max_size: int,
        items: Optional[dict[KT, VT]] = None,
        timeout: Optional[Union[float, int, timedelta]] = None,
    ) -> None:
        self._items: dict[KT, _Expirable[VT]] = LRU(max_size)

        if isinstance(timeout, timedelta):
            timeout = timeout.total_seconds()

        if items:
            for key, value in items.items():
                self._items[key] = _Expirable(value, timeout)

        self._timeout = timeout
