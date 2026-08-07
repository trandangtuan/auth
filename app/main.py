from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import init_db
from app.routers import auth
from app.routers.views import router as view_router
from app.routers.oauth import router as oauth_router
from app.core.exceptions import register_exception_handlers

app = FastAPI(title=settings.APP_NAME)
app.mount("/templates", StaticFiles(directory="templates"), name="templates")

app.include_router(auth, prefix="/api/auth", tags=["auth"])
app.include_router(view_router, tags=["views"])
app.include_router(oauth_router, tags=["oauth"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
