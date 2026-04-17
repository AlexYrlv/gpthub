from fpiaioact import ActorApp

from ..constants import ACTOR
from . import memorize


def init(name: str) -> ActorApp:
    return ActorApp(name).register({
        ACTOR.memorize.name: memorize.init,
    })
