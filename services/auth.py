from uuid import uuid4

from adapters.cache import cache_factory
from services.user import UserService


class AuthService():
    def __init__(self) -> None:
        self.cache = cache_factory()
        self.user_service = UserService()
    
    
    async def validate_token(self, user_id: str, token: str) -> bool:
        cached_token = await self.cache.get_auth_token(user_id)
        
        if cached_token and cached_token == token:
            return True
        
        return False


    async def generate_token(self, user_id: str) -> str:
        token = str(uuid4())
        
        await self.cache.set_auth_token(user_id, token)
        return token
