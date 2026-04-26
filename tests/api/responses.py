from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from gpthub.structures import ChatResponse, ModelList

T = TypeVar("T")


class JSONResponseDict(ABC):

    @classmethod
    @abstractmethod
    def create(cls, response: dict) -> T:
        raise NotImplementedError()

    @abstractmethod
    def to_dict(self) -> dict:
        raise NotImplementedError()


class ChatResponseAPI(ChatResponse, JSONResponseDict):
    pass


class ModelListAPI(ModelList, JSONResponseDict):
    pass
