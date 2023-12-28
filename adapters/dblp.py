import requests

from http import HTTPStatus
from typing import Dict, List

from lingua import Language, LanguageDetectorBuilder

from adapters.cache import cache_factory
from adapters.db import db_factory
from exceptions import DependencyException
from schemas.publication import Publication
from schemas.venue import Venue


class DBLPAdapter():
    def __init__(self) -> None:
        self.publication_url = "https://dblp.org/search/publ/api"
        self.author_url = "https://dblp.org/search/author/api"
        self.venue_url = "https://dblp.org/search/venue/api"
        self.cache = cache_factory()
        self.db = db_factory()
        self.languages = [Language.PORTUGUESE, Language.ENGLISH]
        self.language_detector = LanguageDetectorBuilder.from_all_languages().build()
        
        
    def get_publications(self, query: str) -> List[Publication]:
        query = query.replace(" ", "+")
        params = {
            "format": "json",
            "h": 20,
            "query": query
        }
        
        cached_response = self.cache.get_dblp_query(query)
        response = cached_response

        if not cached_response:
            response = requests.get(self.publication_url, params=params)
            
            if response.status_code != 200:
                raise DependencyException(dependency=f"dblp-publication (status code {response.status_code})", status_code=HTTPStatus.FAILED_DEPENDENCY)
            
            self.cache.set_dblp_query(query, response.json())
            
            response = response.json()
        
        if 'hit' not in response['result']['hits']:
            return []

        result = response['result']['hits']['hit']
        publications = self.sanitize_publications(result)
        
        if len(publications) == 0:
            return []
        
        return publications
        
    
    def sanitize_publications(self, publications: List[Dict]) -> List[Publication]:
        sanitized_publications = []
        
        for publication in publications:
            if self.language_detector.detect_language_of(publication["info"]["title"]) in self.languages:
                if "authors" in publication['info']:
                    author = publication['info']['authors']['author']
                    
                    if isinstance(author, Dict):
                        author['pid'] = author['@pid']
                        author['name'] = author['text'] 
                        authors = publication['info']['authors']
                        publication['info']['authors'] = [authors['author']]
                    elif isinstance(author, List):
                        for author in publication['info']['authors']['author']:
                            author['pid'] = author['@pid']
                            author['name'] = author['text']
                    
                    if "author" in publication['info']['authors']:
                        publication['info']['authors'] = publication['info']['authors']['author']
                else:
                    publication['info']['authors'] = []
                
                if 'venue' in publication['info'] and not type(publication['info']['venue']) == str:
                    publication['info']['venue'] = '; '.join(publication['info']['venue'])
                sanitized_publications.append(Publication(**publication['info']))

        return sanitized_publications

    
    def get_venue(self, query: str) -> Venue | None:
        params = {
            "format": "json",
            "query": query
        }
        
        cached_response = self.cache.get_venue(query)
        response = cached_response
        
        if cached_response:
            return Venue(**cached_response)

        db_venue = self.db.get_venue(query)
        
        if db_venue:
            self.cache.set_venue(query, db_venue)
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
        self.cache.set_venue(query, venue.model_dump())
        
        return venue
