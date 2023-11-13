from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from services.auth import AuthService

auth_service = AuthService()


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        skip_routes = [
            "/auth/generate_token",
            "/auth/validate_token",
            "/qualis/update_spreadsheets"
        ]
        
        skip_prefixes = [
            "/user",
            "/venue",
            "/docs",
            "/openapi.json"
        ]

        if request.url.path in skip_routes and request.method == "POST" or request.url.path in skip_prefixes:
            return await call_next(request)
        
        auth_token = request.headers.get('Authorization')
        user_id = request.headers.get('UserId')
    
        if not auth_token:
            return JSONResponse(status_code=403, content={"message": "Authorization token missing"})
        
        if not auth_service.validate_token(user_id, auth_token):
            return JSONResponse(status_code=403, content={"message": "Authorization token invalid"})
        
        response = await call_next(request)

        return response
