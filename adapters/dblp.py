import requests

from http import HTTPStatus
from typing import Dict, List

from adapters.cache import cache_factory
from adapters.db import db_factory
from exceptions import DependencyException
from schemas.venue import Venue


class DBLPAdapter():
    def __init__(self) -> None:
        self.publication_url = "https://dblp.org/search/publ/api"
        self.author_url = "https://dblp.org/search/author/api"
        self.venue_url = "https://dblp.org/search/venue/api"
        self.cache = cache_factory()
        self.db = db_factory()
        
        
    async def get_publications(self, query: str) -> List[Dict]:
        query = query.replace(" ", "+")
        params = {
            "format": "json",
            "h": 15,
            "query": query
        }
        
        cached_response = await self.cache.get_dblp_query(query)
        response = cached_response

        if not cached_response:
            try:
                response = requests.get(self.publication_url, params=params)
            except requests.ConnectTimeout:
                raise DependencyException(dependency=f"dblp-publication timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)
                
            if response.status_code != 200:
                raise DependencyException(dependency=f"dblp-publication (status code {response.status_code})", status_code=HTTPStatus.FAILED_DEPENDENCY)
            
            await self.cache.set_dblp_query(query, response.json())
            
            response = response.json()
        
        if 'hit' not in response['result']['hits']:
            return []

        return response['result']['hits']['hit']

    
    async def get_venue(self, query: str) -> Venue | None:
        params = {
            "format": "json",
            "query": query
        }
        
        cached_response = await self.cache.get_venue(query)
        response = cached_response
        
        if cached_response:
            return Venue(**cached_response)

        db_venue = self.db.get_venue(query)
        
        if db_venue:
            await self.cache.set_venue(query, db_venue)
            return Venue(**db_venue)
        
        response = requests.get(self.venue_url, params=params)
        
        if response.status_code != 200:
            raise DependencyException(dependency=f"dblp-venue (status code {response.status_code})", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
        response = response.json()
        
        if 'hit' not in response['result']['hits']:
            return None

        result = response['result']['hits']['hit']
        
        if not result:
            return None
        
        result = result[0]
        result['score'] = result['@score']
        result['id'] = result['@id']
        result['query'] = query
        
        venue = Venue(**result)
        
        self.db.create_venue(venue)
        await self.cache.set_venue(query, venue.model_dump())
        
        return venue
