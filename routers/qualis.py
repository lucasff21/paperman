from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from utils.qualis import update_files

router = APIRouter(prefix="/qualis")


@router.post("/update_spreadsheets")
def update_spreadsheets(request: Request):
    update_files()
    
    return JSONResponse({"message": "Qualis spreadsheets updated successfully"})

