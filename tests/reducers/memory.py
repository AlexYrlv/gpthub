from __future__ import annotations

from dataclasses import replace

from gpthub.structures import Memory


def change_memory_fact(memory: Memory, fact: str) -> Memory:
    return replace(memory, fact=fact)


def change_memory_source(memory: Memory, source: str) -> Memory:
    return replace(memory, source=source)


def change_memory_user_id(memory: Memory, user_id: str) -> Memory:
    return replace(memory, user_id=user_id)
