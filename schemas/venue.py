from pydantic import BaseModel


class VenueInfo(BaseModel):
    venue: str
    type: str
    url: str
    

class Venue(BaseModel):
    score: int
    id: int
    info: VenueInfo
    url: str
