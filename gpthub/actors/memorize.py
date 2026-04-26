from __future__ import annotations

from logging import getLogger

from fpiaioact import Actor, ActorSystem

from ..controls import MemoryControl
from ..models import MemorizeData
from ..rpc import MemorizeRPC
from ..structures import ChatRequest

LOGGER = getLogger("actors.memorize")


def init(actors: ActorSystem) -> ActorSystem:
    actors.add(MemorizeWorker())
    return actors


class MemorizeWorker(Actor):
    logger = LOGGER
    attempts = 3

    def __init__(self):
        self.rpc = MemorizeRPC()
        self.memory = MemoryControl()
        self.counter = 0

    async def __call__(self):
        oid, message = await self.rpc.wait()

        if message is None:
            return None

        try:
            await self.on_message(message)
        except Exception as error:
            if self.counter < self.attempts:
                return await self.on_error(oid, error)
            return await self.on_save(oid, error)
        return await self.on_success(oid)

    async def on_message(self, data: MemorizeData) -> None:
        request = ChatRequest.create({"model": data.model, "messages": data.messages})
        saved = await self.memory.memorize(request, uid=data.uid)
        self.logger.debug("[%s] Memorized %s facts", data.request_id, len(saved))

    async def on_success(self, oid: str):
        self.counter = 0
        await self.rpc.done(oid)
        return await self.wait()

    async def on_error(self, oid: str, error: Exception):
        self.counter += 1
        self.logger.warning("[%s] Memorize attempt %d failed: %s", oid, self.counter, error)
        await self.rpc.retry(oid)
        return await self.wait()

    async def on_save(self, oid: str, error: Exception):
        self.logger.error("[%s] Memorize gave up after %d attempts: %s", oid, self.attempts, error)
        self.counter = 0
        await self.rpc.done(oid)
        return await self.wait()
