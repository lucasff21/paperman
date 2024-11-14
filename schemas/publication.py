from typing import List, Optional

from pydantic import BaseModel, Field


class Author(BaseModel):
    pid: str
    name: str


class Publication(BaseModel):
    authors: List[Author]
    title: str
    venue: Optional[str] = None
    key: Optional[str] = None
    year: int
    access: Optional[str] = None
    type: str
    ee: Optional[str] = None
    url: str
    publisher: Optional[str] = None
    score: Optional[float] = Field(return_in_api=False, default=None)


class Evaluation(BaseModel):
    url: str
    score: str
    evaluation: str
