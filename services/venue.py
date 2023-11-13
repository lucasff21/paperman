from http import HTTPStatus
from typing import Dict

from adapters.cache import cache_factory
from adapters.db import db_factory
from exceptions import BusinessException
from schemas.venue import Venue


class VenueService:
    def __init__(self) -> None:
        self.cache = cache_factory()
        self.db = db_factory()
    
    
    def create_venue(self, data: Dict) -> None:
        venue = self.db.get_venue(data['query'])
        
        if venue:
            raise BusinessException('Venue already exists', status_code=HTTPStatus.CONFLICT)
        
        self.db.create_venue(Venue(**data))
        self.cache.set_venue(data['query'], data)
    
    
    def get_venue(self, query: str) -> Venue:
        cached_venue = self.cache.get_venue(query)
        
        if cached_venue:
            return Venue(**cached_venue)

        venue = self.db.get_venue(query)
        
        if not venue:
            raise BusinessException('Venue not found', status_code=HTTPStatus.NOT_FOUND) 
        
        venue.pop('_id', None)
        self.cache.set_venue(venue['query'], venue)
        return Venue(**venue)
    
    
    def update_venue(self, data: Dict) -> None:
        venue = Venue(**self.db.get_venue(data['query']))

        if not venue:
            raise BusinessException('Venue not found', status_code=HTTPStatus.NOT_FOUND)
        
        self.db.update_venue(data)
        self.cache.set_venue(data['query'], data)
