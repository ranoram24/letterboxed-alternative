from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecommendationCache(Base):
    """One row per user — the "Recommended for You" picks are only recomputed (a Claude +
    TMDb call) once per CACHE_TTL, not on every home page load."""

    __tablename__ = "recommendation_cache"

    user_email: Mapped[str] = mapped_column(ForeignKey("users.email"), primary_key=True)
    payload: Mapped[list[dict]] = mapped_column(JSON)
    computed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
