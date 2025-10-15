from fastapi import APIRouter
from fastapi.requests import Request

api_v1_router = APIRouter(
    prefix="/api/v1",
)


@api_v1_router.get("/", tags=["General"])
async def healthcheck(_: Request) -> dict[str, str]:
    return {"status": "ok"}


api_v1_sub_routers: tuple = ()

for router in api_v1_sub_routers:
    api_v1_router.include_router(router)
