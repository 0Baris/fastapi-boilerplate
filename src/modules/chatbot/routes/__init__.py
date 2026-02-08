from fastapi import APIRouter

from src.modules.chatbot.routes.uploads import router as upload_router
from src.modules.chatbot.routes.websocket import docs_router, router as websocket_router

router = APIRouter()
router.include_router(websocket_router)
router.include_router(upload_router)

__all__ = ["router", "docs_router"]
