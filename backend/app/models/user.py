from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    # Google's stable subject id, stored for reference/future use. Login upserts by
    # email (the PK) since that's the identity this table is keyed on.
    google_sub: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    profile_picture_url: Mapped[str | None] = mapped_column(String, nullable=True)
    prefs: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    diary_entries: Mapped[list["DiaryEntry"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    lists: Mapped[list["MovieList"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
