# cachingutils

Utilities to make caching data easier

## Examples

Basic caching:

```py
from cachingutils import cached


@cached()
def fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(100))  # 633825300114114700748351602688
```

Caching with your own cache object:

```py
from cachingutils import Cache, cached


my_cache = Cache()

@cached(cache=my_cache)
def fib(n: int) -> int:
    if n < 2:
        return n
    return fib(n - 1) + fib(n - 2)

print(fib(100))  # 633825300114114700748351602688
```

Async caching:

```py
from asyncio import run

from cachingutils import acached


@acached()
async def fib(n: int) -> int:
    if n < 2:
        return n
    return await fib(n - 1) + await fib(n - 2)

print(run(fib(100)))  # 633825300114114700748351602688
```

Caching specific positional args:

```py
from cachingutils import cached


@cached(include_posargs=[0])
async def add(a: int, b: int) -> int:
    return a + b

print(add(1, 2))  # 3
print(add(2, 2))  # 3
print(add(2, 3))  # 5
```

Caching specific keyword args:

```py
from cachingutils import cached


@cached(include_posargs=[0], include_kwargs=['c'])
def add(a: int, b: int, *, c: int) -> int:
    return a + b

print(add(1, 2, c=3))  # 3
print(add(2, 2, c=3))  # 4
print(add(2, 3, c=3))  # 4
```

Caching with a timeout:

```py
from time import sleep

from cachingutils import cached


@cached(timeout=1, include_posargs=[0])
def add(a: int, b: int) -> int:
    return a + b

print(add(1, 2))  # 3
print(add(1, 3))  # 3
sleep(2)
print(add(1, 3))  # 4
```

Using a raw `Cache` object:

```py
from time import sleep

from cachingutils import Cache


my_cache: Cache[str, int] = Cache(timeout=5)

my_cache["abc"] = 123

print(my_cache["abc"])  # 123

sleep(6)

print(my_cache["abc"])  # KeyError: 'abc'
```
