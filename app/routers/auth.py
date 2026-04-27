import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.core.security import (
    generate_session_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.deps import templates
from app.utils.db import (
    count_users,
    create_user,
    create_session,
    delete_session_by_token,
    get_user_by_username,
    touch_last_login,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if await count_users() == 0:
        return RedirectResponse(url="/setup", status_code=302)

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "error": None,
        },
    )


@router.post("/token")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    if await count_users() == 0:
        raise HTTPException(status_code=403, detail="Initial setup required")

    user = await get_user_by_username(form_data.username)

    if (
        not user
        or not int(user["is_active"])
        or not verify_password(form_data.password, user["password_hash"])
    ):
        logger.warning(
            "Login fallit per usuari=%s ip=%s",
            form_data.username,
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(status_code=400, detail="Usuari o contrasenya incorrectes")

    session_token = generate_session_token()
    await create_session(user_id=int(user["id"]), session_token=session_token)
    await touch_last_login(int(user["id"]))

    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        samesite="lax",
        path="/",
    )

    logger.info(
        "Login correcte usuari=%s ip=%s",
        form_data.username,
        request.client.host if request.client else "unknown",
    )
    return {"status": "success"}


@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    if await count_users() > 0:
        return RedirectResponse(url="/login", status_code=302)

    return templates.TemplateResponse(
        request,
        "setup.html",
        {
            "request": request,
            "error": None,
        },
    )


@router.post("/setup", response_class=HTMLResponse)
async def setup_first_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if await count_users() > 0:
        return RedirectResponse(url="/login", status_code=302)

    username = username.strip()
    if not username:
        return templates.TemplateResponse(
            request,
            "setup.html",
            {
                "request": request,
                "error": "Nom d'usuari buit",
            },
            status_code=400,
        )

    try:
        validate_password_strength(password)
        user_id = await create_user(
            username=username,
            password_hash=hash_password(password),
            is_active=True,
        )
    except HTTPException as exc:
        return templates.TemplateResponse(
            request,
            "setup.html",
            {
                "request": request,
                "error": exc.detail,
            },
            status_code=exc.status_code,
        )

    session_token = generate_session_token()
    await create_session(user_id=user_id, session_token=session_token)
    await touch_last_login(user_id)

    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        samesite="lax",
        path="/",
    )

    logger.info(
        "Bootstrap completat usuari=%s ip=%s",
        username,
        request.client.host if request.client else "unknown",
    )
    return response


@router.get("/logout")
async def logout(request: Request):
    logger.info(
        "Logout ip=%s",
        request.client.host if request.client else "unknown",
    )

    session_token = request.cookies.get("session_id")
    if session_token:
        await delete_session_by_token(session_token)

    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_id", path="/")
    return response
