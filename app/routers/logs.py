from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from app.core.security import get_current_user
from app.deps import templates
from app.services.log_service import tail_log

router = APIRouter()


@router.get("/logs", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def view_logs(
    request: Request,
    lines: int = Query(default=200, ge=1, le=2000),
    q: str = Query(default=""),
    embedded: int = Query(default=0),
):
    entries = tail_log(lines=lines, query=q or None)
    return templates.TemplateResponse(
        request,
        "logs.html",
        {
            "request": request,
            "entries": entries,
            "lines": lines,
            "query": q,
            "embedded": embedded,
        },
    )
