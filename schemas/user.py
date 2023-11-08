from typing import List

from pydantic import BaseModel


class Source(BaseModel):
    service: str
    url: str


class User(BaseModel):
    _id: str
    sources: List[Source]
