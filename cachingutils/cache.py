from time import sleep, time
from typing import Generic, TypeVar

KT = TypeVar("KT")
VT = TypeVar("VT")
T = TypeVar("T")


class _Expirable(Generic[VT]):
    """
    Base class for objects that can expire.
    """

    def __init__(self, value: VT, timeout: float = None) -> None:
        self.value = value

        self._expires = timeout + time() if timeout else None

    @property
    def expired(self) -> bool:
        if not self._expires:
            return False
        return self._expires < time()


class Cache(Generic[KT, VT]):
    def __init__(self, values: dict[KT, VT] = None, timeout: float = None) -> None:
        self._items: dict[KT, _Expirable[VT]] = (
            {key: _Expirable(values, timeout) for key, values in values.items()}
            if values
            else {}
        )
        self._timeout = timeout

    def __getitem__(self, key: KT) -> VT:
        item = self._items[key]

        if item.expired:
            raise KeyError(key)

        return item.value

    def __setitem__(self, key: KT, value: VT) -> None:
        self._items[key] = _Expirable(value, self._timeout)

    def get(self, key: KT, default: T | None = None) -> VT | T | None:
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key: KT) -> bool:
        return key in self._items and not self._items[key].expired
