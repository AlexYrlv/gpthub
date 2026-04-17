from __future__ import annotations

from logging import Logger, getLogger


class LoggerMixin:
    logger: Logger = getLogger()

    def __new__(cls, *_, **__):
        obj = super().__new__(cls)
        obj.logger = cls.logger.getChild(f"{cls.__name__}")
        return obj


class Cacheable:

    def __repr__(self):
        return type(self).__name__


class BaseResource(LoggerMixin):
    logger = getLogger("api")


class BaseControl(LoggerMixin):
    logger = getLogger("control")


class BaseAPI(LoggerMixin, Cacheable):
    logger = getLogger("rest")


class BaseRPC(LoggerMixin):
    logger = getLogger("rpc")
