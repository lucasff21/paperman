from bson import ObjectId
from functools import lru_cache
from http import HTTPStatus
from typing import Dict, List

from decouple import config
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ServerSelectionTimeoutError

from exceptions import DependencyException


@lru_cache(maxsize=config('DB_MAX_INSTANCES', cast=int))
def db_factory():
    return DB()


class DB():
    def __init__(self) -> None:
        self.client = MongoClient(config('DB_URL'))
        self.db = self.client['paperman']
        self.users: Collection = self.db.users


    def create_user(self, sources: List[Dict]) -> str:
        data = {
            "sources": sources
        }
        
        try:
            user = self.users.insert_one(data)
        except ServerSelectionTimeoutError:
            raise DependencyException(dependency="db", status_code=HTTPStatus.FAILED_DEPENDENCY)

        return str(user.inserted_id)
        
    
    def get_user(self, id: str)-> (Dict | None):
        try:
            return self.users.find_one({"_id": ObjectId(id)})
        except ServerSelectionTimeoutError:
            raise DependencyException(dependency="db", status_code=HTTPStatus.FAILED_DEPENDENCY)
    
    def edit_user_sources(self, id: str, sources: List[Dict]) -> bool:
        try:
            result = self.users.update_one(
                {"id": id}, 
                {"sources": sources}
            )
        except ServerSelectionTimeoutError:
            raise DependencyException(dependency="db", status_code=HTTPStatus.FAILED_DEPENDENCY)
        
        if result.matched_count > 0 and result.modified_count > 0:
            return True
        
        return False
