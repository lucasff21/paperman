from http import HTTPStatus

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.publication import PublicationService

router = APIRouter(prefix="/publications")

publication_service = PublicationService()


@router.get("")
def get_publications(request: Request):
    user = request.headers.get('UserId')
    
    if not user:
        return JSONResponse({"message": "Missing data on payload"}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    publications = publication_service.get_publications(user)
    
    return JSONResponse({"publications": [item.model_dump() for item in publications]})

