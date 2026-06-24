from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import pic

app = FastAPI(title="Thufail PIC Data Portal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(pic.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
