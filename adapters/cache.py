import json

from functools import lru_cache
from http import HTTPStatus
from typing import Dict

from decouple import config
from redis import Redis
from redis.exceptions import ConnectionError

from enums import Time
from exceptions import DependencyException


@lru_cache(maxsize=config('CACHE_MAX_INSTANCES', cast=int))
def cache_factory():
    return Cache()


class Cache():
    def __init__(self) -> None:
        self.conn = Redis(host=config('CACHE_HOST'), port=config(
            'CACHE_PORT'), password=config('CACHE_PASS'), health_check_interval=10)

    
    def set_dblp_query(self, query: str, response: Dict) -> None:
        key = f"dblp-query:{query}"
        try:
            self.conn.set(name=key, value=json.dumps(response), ex=Time.DAY)
        except ConnectionError:
            raise DependencyException(dependency="cache", status_code=HTTPStatus.FAILED_DEPENDENCY)
    
    
    def get_dblp_query(self, query: str) -> Dict | None:
        key = f"dblp-query:{query}"
        
        try:
            object = self.conn.get(key)
        except ConnectionError:
            raise DependencyException(dependency="cache", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
        return None if not object else json.loads(object)
    
    
    def set_orcid_public_records(self, id: str, public_records: Dict):
        key = f"orcid-public-records:{id}"
        
        try:
            self.conn.set(name=key, value=public_records, ex=Time.DAY)
        except ConnectionError:
            raise DependencyException(dependency="cache", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
    
    def get_orcid_public_records(self, id: str) -> Dict | None:
        key = f"orcid-public-records:{id}"
        
        try:
            object = self.conn.get(key)
        except ConnectionError:
            raise DependencyException(dependency="cache", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
        return None if not object else json.loads(object)
    
    
    def set_auth_token(self, user_id: str, token: str) -> None:
        key = f"auth-token:{user_id}"
        
        try:
            self.conn.set(name=key, value=token, ex=Time.DAY)
        except ConnectionError:
            raise DependencyException(dependency="cache", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
    
    def get_auth_token(self, user_id: str) -> None:
        key = f"auth-token:{user_id}"
        
        try:
            object = self.conn.get(key)
        except ConnectionError:
            raise DependencyException(dependency="cache", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
        return None if not object else object.decode()
    
    
    def set_venue(self, query: str, data: Dict) -> None:
        key = f"venue:{query}"
        
        try:
            self.conn.set(name=key, value=json.dumps(data), ex=Time.DAY)
        except ConnectionError:
            raise DependencyException(dependency="cache", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
    
    def get_venue(self, query: str) -> str | None:
        key = f"venue:{query}"
        
        try:
            object = self.conn.get(key)
        except ConnectionError:
            raise DependencyException(dependency="cache", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
        return None if not object else json.loads(object)
