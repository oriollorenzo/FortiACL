from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.core.logging import setup_logging
from app.routers.auth import router as auth_router
from app.routers.ui import router as ui_router
from app.routers.settings import router as settings_router
from app.routers.switches import router as switches_router
from app.routers.logs import router as logs_router
from app.routers.acl_hits import router as acl_hits_router
from app.utils.db import init_auth_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await init_auth_tables()

    yield


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
app.state.templates = templates

app.include_router(auth_router)
app.include_router(ui_router)
app.include_router(settings_router)
app.include_router(switches_router)
app.include_router(logs_router)
app.include_router(acl_hits_router)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
