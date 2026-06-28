from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.VERSION}


from app.api.v1.api import api_router

app.include_router(api_router, prefix=settings.API_V1_STR)
