from fastapi import APIRouter
from app.api.v1.endpoints import servers, websocket, events, reports, bulk, discovery, scheduler

api_router = APIRouter()
api_router.include_router(servers.router, prefix="/servers", tags=["servers"])
api_router.include_router(websocket.router, prefix="/ws")
api_router.include_router(events.router, prefix="/events", tags=["events"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(bulk.router, prefix="/bulk", tags=["bulk"])
api_router.include_router(discovery.router, prefix="/discovery", tags=["discovery"])
api_router.include_router(scheduler.router, prefix="/scheduler", tags=["scheduler"])
