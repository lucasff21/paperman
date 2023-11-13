from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.venue import VenueService

router = APIRouter(prefix="/venue")

venue_service = VenueService()


@router.get("")
def get_venue(query: str):
    return JSONResponse({"user": venue_service.get_venue(query).model_dump()})


@router.post("")
async def create_venue(request: Request):
    data = await request.json()
    venue_service.create_venue(data)
    return JSONResponse({"message": "Venue created successfully"})


@router.patch("")
async def update_venue(request: Request):
    data = await request.json()
    venue_service.update_venue(data)
    return JSONResponse({"message": "Venue updated successfully"})
