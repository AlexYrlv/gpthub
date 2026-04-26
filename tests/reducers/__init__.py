from typing import TypeVar

T = TypeVar("T")


def batch(item: T, *reducers) -> T:
    result = item
    for reduce in reducers:
        result = reduce[0](result, **reduce[1]) if isinstance(reduce, tuple) else reduce(result)
    return result
