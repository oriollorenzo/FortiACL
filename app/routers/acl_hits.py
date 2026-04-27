from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.core.security import get_current_user
from app.deps import templates
from app.services.acl_hits_service import (
    get_acl_hit_samples_page,
    get_acl_hit_sample_campuses,
    scan_acl_hits_for_campus,
    clear_acl_hit_samples,
    clear_filtered_acl_hit_samples,
)

class ACLHitsScanPayload(BaseModel):
    serials: list[str] = []

router = APIRouter()

@router.post("/acl-hits/scan/{nom_campus}", dependencies=[Depends(get_current_user)])
async def scan_acl_hits(nom_campus: str, payload: ACLHitsScanPayload):
    return await scan_acl_hits_for_campus(nom_campus, serials=payload.serials)


@router.post("/acl-hits/samples/clear", dependencies=[Depends(get_current_user)])
async def acl_hits_samples_clear():
    return await clear_acl_hit_samples()


@router.post("/acl-hits/samples/clear-filtered", dependencies=[Depends(get_current_user)])
async def acl_hits_samples_clear_filtered(
    q: str = Query(default=""),
    campus: str = Query(default=""),
    severity: str = Query(default=""),
):
    return await clear_filtered_acl_hit_samples(
        q=q,
        campus=campus,
        severity=severity,
    )

@router.get("/acl-hits", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def acl_hits_view(
    request: Request,
    q: str = Query(default=""),
    campus: str = Query(default=""),
    severity: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=100, ge=20, le=500),
    embedded: int = Query(default=0),
    sort_by: str = Query(default="created_at"),
    sort_dir: str = Query(default="desc"),
):
    sample_page = await get_acl_hit_samples_page(
        page=page,
        per_page=per_page,
        q=q,
        campus=campus,
        severity=severity,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    campus_options = await get_acl_hit_sample_campuses()

    return templates.TemplateResponse(
        request,
        "acl_hits.html",
        {
            "request": request,
            "samples": sample_page["items"],
            "page": sample_page["page"],
            "pages": sample_page["pages"],
            "per_page": sample_page["per_page"],
            "total": sample_page["total"],
            "q": q,
            "campus": campus,
            "severity": severity,
            "embedded": embedded,
            "campus_options": campus_options,
            "sort_by": sample_page["sort_by"],
            "sort_dir": sample_page["sort_dir"],
        },
    )
