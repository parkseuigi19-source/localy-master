from fastapi import APIRouter

router = APIRouter(
    prefix="/trips",
    tags=["trips"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def read_trips():
    return {"message": "Trips router"}
