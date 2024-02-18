from http import HTTPStatus

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.publication import PublicationService
from services.user import UserService

router = APIRouter(prefix="/publications")

publication_service = PublicationService()
user_service = UserService()


@router.post("")
async def publications(request: Request):
    user = request.headers.get('UserId')
    
    if not user:
        return JSONResponse({"message": "Missing data on payload"}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    publications = await publication_service.get_publications(user)
    user_service.update_recommendations(user, publications)
    
    return JSONResponse({"publications": [item.model_dump() for item in publications]})


@router.post("/demo")
async def demo(request: Request):
    data = await request.json()
    
    orcid = data.get('orcid')
    
    if not orcid:
        return JSONResponse({"message": "Missing data on payload"}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    return await publication_service.demo(orcid)
    