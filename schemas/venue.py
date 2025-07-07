from typing import List, Optional, Union
from pydantic import BaseModel, field_validator


class VenueInfo(BaseModel):
    venue: Optional[str] = None
    type: str
    url: str

    @field_validator("venue")
    def validate_venue(cls, value: Union[str, List[str]]) -> str:
        if not value:
            return None
        
        if isinstance(value, list):
            return ', '.join(map(str, value))
        
        return value
    

class Venue(BaseModel):
    score: int
    id: int
    info: VenueInfo
    url: str
    query: Optional[str] = None
