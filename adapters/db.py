from bson import ObjectId
from functools import lru_cache
from http import HTTPStatus
from typing import Dict, List

from decouple import config
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import ServerSelectionTimeoutError

from exceptions import DependencyException
from schemas.venue import Venue


@lru_cache(maxsize=config("DB_MAX_INSTANCES", cast=int))
def db_factory():
    return DB()


class DB:
    def __init__(self) -> None:
        self.client = MongoClient(config("DB_URL"))
        self.db = self.client["paperman"]
        self.users: Collection = self.db.users
        self.venues: Collection = self.db.venues
        self.evaluations: Collection = self.db.evaluations
        self.ratings: Collection = self.db.ratings

    def create_user(self, sources: List[Dict], interests: List[str] = None) -> str:
        data = {
            "sources": sources,
            "interests": interests if interests else [],
            "recommendations": []
        }

        try:
            user = self.users.insert_one(data)
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

        return str(user.inserted_id)

    def get_user(self, id: str) -> (Dict | None):
        try:
            return self.users.find_one({"_id": ObjectId(id)})
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def edit_user_data(self, id: str, sources: List[Dict] = None, interests: List[str] = None) -> bool:
        update_fields = {}
        if sources is not None:
            update_fields["sources"] = sources
        if interests is not None:
            update_fields["interests"] = interests

        try:
            result = self.users.update_one(
                {"_id": ObjectId(id)},
                {"$set": update_fields}
            )
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

        if result.matched_count > 0:
            return True

        return False

    def create_venue(self, venue: Venue) -> None:
        try:
            self.venues.insert_one(venue.model_dump())
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def get_venue(self, query: str) -> (Dict | None):
        try:
            return self.venues.find_one({"query": query}, {"_id": False})
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def update_venue(self, data: Dict) -> (Dict | None):
        try:
            return self.venues.replace_one(
                {"query": data["query"]},
                data
            )
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def update_recommendations(self, id: str, recommendations: List[str]) -> None:
        try:
            self.users.update_one(
                {"_id": ObjectId(id)},
                {"$addToSet": {
                    "recommendations": {
                        "$each": recommendations
                    }
                }}
            )
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def set_evaluation(self, data) -> None:
        try:
            self.evaluations.insert_one(data)
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def set_rating(self, data: Dict) -> None:
        try:
            self.ratings.update_one(
                {"user_id": data["user_id"], "url": data["url"]},
                {"$set": data},
                upsert=True
            )
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def get_rating(self, query: Dict) -> (Dict | None):
        try:
            return self.ratings.find_one(query)
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def save(self, collection: str, data: Dict) -> None:
        try:
            self.db.get_collection(collection).insert_one(data)
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)

    def retrieve(self, collection: str, query: Dict) -> (Dict | None):
        try:
            return self.db.get_collection(collection).find_one(query)
        except ServerSelectionTimeoutError:
            raise DependencyException(
                dependency="db-timeout", status_code=HTTPStatus.FAILED_DEPENDENCY)
