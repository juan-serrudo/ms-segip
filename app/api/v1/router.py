"""Enrutador principal de la API versión 1."""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.pdf import router as pdf_router
from app.api.v1.segip import router as segip_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router)
api_v1_router.include_router(segip_router)
api_v1_router.include_router(pdf_router)
