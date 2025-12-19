from fastapi import APIRouter

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)

@router.get("/")
async def read_agents():
    return {"message": "Agents router"}
