from authlib.integrations.starlette_client import OAuthError
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserOut
from app.services.auth_service import SESSION_USER_KEY, oauth, upsert_user_from_userinfo

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/login/google")
async def login_google(request: Request):
    settings = get_settings()
    return await oauth.google.authorize_redirect(request, settings.google_redirect_uri)


@router.get("/callback/google")
async def callback_google(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error

    userinfo = token.get("userinfo")
    if userinfo is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Google did not return userinfo"
        )

    user = upsert_user_from_userinfo(db, dict(userinfo))
    db.commit()

    request.session[SESSION_USER_KEY] = user.email
    return RedirectResponse(url=get_settings().frontend_url)


@router.post("/logout")
async def logout(request: Request):
    request.session.pop(SESSION_USER_KEY, None)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
