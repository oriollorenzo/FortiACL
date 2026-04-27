import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.config import settings
from app.deps import templates
from app.utils.db import count_users, get_session_with_user_by_token

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    logger.info("Accés a portada ip=%s", request.client.host if request.client else "unknown")

    if await count_users() == 0:
        return RedirectResponse(url="/setup", status_code=302)

    token = request.cookies.get("session_id")
    if not token:
        return RedirectResponse(url="/login", status_code=302)

    session_row = await get_session_with_user_by_token(token)
    if not session_row or not int(session_row["is_active"]):
        response = RedirectResponse(url="/login", status_code=302)
        response.delete_cookie("session_id", path="/")
        return response

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "request": request,
            "project_name": settings.PROJECT_NAME,
            "user": session_row["username"],
        },
    )
