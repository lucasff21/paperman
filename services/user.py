from http import HTTPStatus
from typing import Dict, List

from adapters.db import db_factory
from exceptions import BusinessException
from schemas.user import User


class UserService:
    def __init__(self) -> None:
        self.db = db_factory()
    
    
    def create_user(self, sources: List[Dict]) -> str:
        user_id = self.db.create_user(sources)
        return user_id
    
    
    def get_user(self, id: str) -> User:
        user = self.db.get_user(id)
        
        if user:
            return User(**user)
        
        raise BusinessException('User not found', status_code=HTTPStatus.NOT_FOUND) 
    
    
    def edit_user_sources(self, id: str, sources: List[Dict]) -> None:
        edit = self.db.edit_user_sources(id, sources)

        if not edit:
            raise BusinessException('Unable to edit provided user sources')