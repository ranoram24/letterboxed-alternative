from authlib.integrations.starlette_client import OAuth
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.user import User

SESSION_USER_KEY = "user_email"


def build_oauth(settings: Settings | None = None) -> OAuth:
    settings = settings or get_settings()
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    return oauth


oauth = build_oauth()


def upsert_user_from_userinfo(db: Session, userinfo: dict) -> User:
    """Create or update the User row for a Google login, keyed by email (the table's PK)."""
    email = userinfo["email"]
    google_sub = userinfo["sub"]
    display_name = userinfo.get("name") or email
    profile_picture_url = userinfo.get("picture")

    user = db.get(User, email)
    if user is None:
        user = User(email=email)
        db.add(user)

    user.google_sub = google_sub
    user.display_name = display_name
    user.profile_picture_url = profile_picture_url

    db.flush()
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))
