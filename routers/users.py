from http import HTTPStatus
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.user import UserService

router = APIRouter(prefix="/user", tags=["user"])

user_service = UserService()


@router.get("")
def get_user(request: Request):
    id = request.headers["UserId"]
    
    return JSONResponse({"user": user_service.get_user(id).model_dump()})


@router.post("")
async def create_user(request: Request):
    payload = await request.json()
    
    sources = []
    interests = []

    if isinstance(payload, list):
        sources = payload
    elif isinstance(payload, dict):
        sources = payload.get("sources", [])
        interests = payload.get("interests", [])
    
    return JSONResponse({"userId": user_service.create_user(sources, interests)})


@router.patch("")
async def edit_user(request: Request):
    user = request.headers.get("UserId")
    
    if not user:
        return JSONResponse({"message": "Missing data on payload"}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    payload = await request.json()
    sources = None
    interests = None

    if isinstance(payload, list):
        # Legacy support: payload is directly the list of sources
        sources = payload
    elif isinstance(payload, dict):
        # New format: payload is an object containing sources and/or interests
        sources = payload.get("sources")
        interests = payload.get("interests")

    user_service.edit_user_data(user, sources, interests)
    
    return JSONResponse({"message": "User data updated successfully"})
