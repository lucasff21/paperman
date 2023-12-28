from typing import Annotated, List, Optional

from pydantic import BaseModel, BeforeValidator, Field

PyObjectId = Annotated[str, BeforeValidator(str)]


class Source(BaseModel):
    service: str
    url: str


class User(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    sources: List[Source]
    recommendations: List[str]
