from fastapi import APIRouter

router = APIRouter(
    prefix="/diary",
    tags=["diary"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def read_diary():
    return {"message": "Diary router"}
