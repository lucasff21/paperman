from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from services.venue import VenueService

router = APIRouter(prefix="/venue")

venue_service = VenueService()


@router.get("")
async def get_venue(query: str):
    venue = await venue_service.get_venue(query)
    return JSONResponse({"user": venue.model_dump()})


@router.post("")
async def create_venue(request: Request):
    data = await request.json()
    await venue_service.create_venue(data)
    return JSONResponse({"message": "Venue created successfully"})


@router.patch("")
async def update_venue(request: Request):
    data = await request.json()
    await venue_service.update_venue(data)
    return JSONResponse({"message": "Venue updated successfully"})
