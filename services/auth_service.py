from uuid import uuid4

from adapters.cache import cache_factory
from services.user_service import UserService


class AuthService():
    def __init__(self) -> None:
        self.cache = cache_factory()
        self.user_service = UserService()
    
    
    def validate_token(self, user_id: str, token: str) -> bool:
        cached_token = self.cache.get_auth_token(user_id)
        
        if cached_token and cached_token == token:
            return True
        
        return False


    def generate_token(self, user_id: str) -> str:
        token = str(uuid4())
        
        self.cache.set_auth_token(user_id, token)
        return token
