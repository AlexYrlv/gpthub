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

    def __init__(self):
        self.rpc = MemorizeRPC()
        self.memory = MemoryControl()

    async def __call__(self):
        oid, message = await self.rpc.wait()

        if message is None:
            return None

        try:
            await self.on_message(message)
        except Exception:
            self.logger.exception("[%s] Memorize failed", oid)

        await self.rpc.done(oid)
        return await self.wait()

    async def on_message(self, data: MemorizeData) -> None:
        request = ChatRequest.create({"model": data.model, "messages": data.messages})
        saved = await self.memory.memorize(request, uid=data.uid)
        self.logger.debug("[%s] Memorized %s facts", data.request_id, len(saved))
