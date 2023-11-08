from http import HTTPStatus

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.auth_service import AuthService

router = APIRouter(prefix="/auth")

auth_service = AuthService()


@router.post("/generate_token")
async def generate_auth_token(request: Request):
    data = await request.json()
    
    if not data['user_id']:
        return JSONResponse({"message": "User ID missing"}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    return JSONResponse({"token": auth_service.generate_token(data['user_id'])})


@router.post("/validate_token")
async def validate_auth_token(request: Request):
    data = await request.json()
    
    if not data['user'] or not data['token']:
        return JSONResponse({"message": "Missing data on payload"}, status_code=422)
    
    return JSONResponse({"valid": auth_service.validate_token(data['user'], data['token'])})

