from fastapi import APIRouter, Depends, Request, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import get_current_user, hash_password, validate_password_strength
from app.deps import templates
from app.services.settings_service import load_settings_from_yaml, save_settings_to_yaml
from app.utils.db import (
    count_active_users,
    create_user,
    delete_sessions_by_user,
    get_user_by_id,
    get_user_by_username,
    list_users,
    set_user_active,
    update_user_password,
)

router = APIRouter()


class CreateUserPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=8, max_length=256)


class UpdatePasswordPayload(BaseModel):
    password: str = Field(min_length=8, max_length=256)


@router.get("/settings", response_class=HTMLResponse, dependencies=[Depends(get_current_user)])
async def settings_ui(
    request: Request,
    embedded: int = Query(default=0),
):
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "request": request,
            "version": settings.current_version,
            "project_name": settings.PROJECT_NAME,
            "user": settings.SWITCH_USER,
            "embedded": embedded,
        },
    )


@router.get("/api/settings", dependencies=[Depends(get_current_user)])
async def get_api_settings():
    return load_settings_from_yaml()


@router.post("/api/settings", dependencies=[Depends(get_current_user)])
async def save_settings(new_config: dict):
    return save_settings_to_yaml(new_config)


@router.get("/api/users", dependencies=[Depends(get_current_user)])
async def api_list_users():
    return {"items": await list_users()}


@router.post("/api/users", dependencies=[Depends(get_current_user)])
async def api_create_user(payload: CreateUserPayload):
    username = payload.username.strip()

    if not username:
        raise HTTPException(status_code=400, detail="Nom d'usuari buit")

    existing = await get_user_by_username(username)
    if existing:
        raise HTTPException(status_code=409, detail="L'usuari ja existeix")

    validate_password_strength(payload.password)

    user_id = await create_user(
        username=username,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    return {"ok": True, "user_id": user_id}


@router.post("/api/users/{user_id}/password", dependencies=[Depends(get_current_user)])
async def api_change_user_password(user_id: int, payload: UpdatePasswordPayload):
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    validate_password_strength(payload.password)
    await update_user_password(user_id, hash_password(payload.password))
    await delete_sessions_by_user(user_id)

    return {"ok": True}


@router.post("/api/users/{user_id}/toggle-active", dependencies=[Depends(get_current_user)])
async def api_toggle_user_active(user_id: int):
    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuari no trobat")

    current_active = bool(user["is_active"])

    if current_active:
        active_count = await count_active_users()
        if active_count <= 1:
            raise HTTPException(status_code=400, detail="No es pot desactivar l'últim usuari actiu")

    await set_user_active(user_id, not current_active)

    if current_active:
        await delete_sessions_by_user(user_id)

    return {"ok": True, "is_active": (not current_active)}
