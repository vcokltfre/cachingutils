from typing import Any, Optional, Protocol


class Cache(Protocol):
    def __getitem__(self, key: Any) -> Any:
        ...

    def __setitem__(self, key: Any, value: Any) -> None:
        ...

    def __contains__(self, key: Any) -> bool:
        ...

    def get(self, key: Any, default: Optional[Any] = None) -> Optional[Any]:
        ...

    def set(self, key: Any, value: Any, timeout: Optional[float] = None) -> None:
        ...


class AsyncCache(Protocol):
    async def get(self, key: Any, default: Optional[Any] = None) -> Optional[Any]:
        ...

    async def set(self, key: Any, value: Any, timeout: Optional[float] = None) -> None:
        ...
