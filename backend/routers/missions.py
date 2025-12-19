from fastapi import APIRouter

router = APIRouter(
    prefix="/missions",
    tags=["missions"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def read_missions():
    return {"message": "Missions router"}
