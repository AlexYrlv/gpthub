from config_fastapi import Config
from redis_rpc_pubsub import PubSub

from .baseclasses import BaseRPC
from .models import MemorizeData


class MemorizeRPC(BaseRPC):
    config = Config(section="rpc")
    redis_config = Config(section="redis")

    def __init__(self):
        self.pubsub = PubSub(
            inbox=self.config.get("memorize_queue", "rpc:memorize"),
            alias=self.redis_config.get("alias"),
        )

    async def send(self, data: MemorizeData) -> None:
        await self.pubsub.publish(oid=data.request_id, value=data)

    async def wait(self) -> tuple[str | None, MemorizeData | None]:
        result = await self.pubsub.subscribe_blocking(MemorizeData)
        return result.oid, result.message

    async def done(self, oid: str) -> None:
        await self.pubsub.done(oid)
