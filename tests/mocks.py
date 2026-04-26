from __future__ import annotations

from contextlib import ExitStack
from typing import Any


class MockStack:
    """Стек patches с именованным доступом к мокам.

    stack = MockStack(name=patch.object(Cls, "method", return_value=...))
    with stack.activate() as mocks:
        mocks["name"]  # Mock instance
    """

    def __init__(self, **patches: Any) -> None:
        self._patches = patches

    def activate(self) -> _MockStackContext:
        return _MockStackContext(self._patches)


class _MockStackContext:
    def __init__(self, patches: dict[str, Any]) -> None:
        self._patches = patches
        self._stack = ExitStack()

    def __enter__(self) -> dict[str, Any]:
        return {name: self._stack.enter_context(patch) for name, patch in self._patches.items()}

    def __exit__(self, *exc: Any) -> None:
        self._stack.close()
