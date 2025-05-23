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
    sources = await request.json()
    
    return JSONResponse({"userId": user_service.create_user(sources)})


@router.patch("")
async def edit_user_sources(request: Request):
    user = request.headers.get("UserId")
    
    if not user:
        return JSONResponse({"message": "Missing data on payload"}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    sources = await request.json()
    user_service.edit_user_sources(user, sources)
    
    return JSONResponse({"message": "User sources updated successfully"})
