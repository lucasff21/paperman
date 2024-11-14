from http import HTTPStatus

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from services.publication import PublicationService
from services.user import UserService

router = APIRouter(prefix="/publications")

publication_service = PublicationService()
user_service = UserService()

templates = Jinja2Templates(directory="templates")


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


@router.post("/evaluation")
async def evaluation(request: Request):
    data = await request.json()
    
    name = data.get('name')
    evaluations = data.get('evaluations')
    comments = data.get('comments')
    
    if not name or not evaluations:
        return JSONResponse({"message": "Missing data on payload"}, status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    publication_service.evaluation(name, evaluations, comments)
    
    return JSONResponse({"message": "Evaluation completed successfully"}, status_code=HTTPStatus.OK)


@router.get("/experiment")
async def experiment(request: Request):
    return templates.TemplateResponse(
        request=request, name="experiment.html"
    )