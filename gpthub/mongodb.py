from __future__ import annotations

from datetime import datetime

from motorengine import Document
from motorengine import fields as f


class DateTimeMixin:
    created_at = f.DateTimeField(default=datetime.now)
    updated_at = f.DateTimeField(default=datetime.now)


class ActiveMixin:
    active = f.BooleanField(default=True)
    deleted = f.BooleanField(default=False)


class MemoryModel(Document, DateTimeMixin, ActiveMixin):
    __collection__ = "memories"

    user_id = f.StringField(required=True)
    fact = f.StringField(required=True)
    source = f.StringField(default="chat")
    embedding = f.ListField(f.FloatField())


class FileContextModel(Document, DateTimeMixin, ActiveMixin):
    __collection__ = "files"

    user_id = f.StringField(required=True)
    filename = f.StringField(required=True)
    content_type = f.StringField()
    chunks = f.ListField(f.StringField())
    embeddings = f.ListField(f.ListField(f.FloatField()))


async def find_memories_by_user(user_id: str) -> list[MemoryModel]:
    return await MemoryModel.objects(user_id=user_id, deleted=False).all()


async def find_files_by_user(user_id: str) -> list[FileContextModel]:
    return await FileContextModel.objects(user_id=user_id, deleted=False).all()
