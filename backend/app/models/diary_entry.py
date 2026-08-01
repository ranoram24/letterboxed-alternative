from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DiaryEntry(Base):
    __tablename__ = "diary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(ForeignKey("users.email"), nullable=False, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False, index=True)
    watched_date: Mapped[date] = mapped_column(Date, nullable=False)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)  # half-star increments, 0.5-5.0
    rewatch: Mapped[bool] = mapped_column(Boolean, default=False)
    review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    liked: Mapped[bool] = mapped_column(Boolean, default=False)
    # 'native' | 'import' — CSV importer isn't built yet, so all rows are 'native' for now
    source: Mapped[str] = mapped_column(String, default="native")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="diary_entries")
    movie: Mapped["Movie"] = relationship()
