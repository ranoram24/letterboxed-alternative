from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)  # minutes
    genres: Mapped[list[str]] = mapped_column(JSON, default=list)
    directors: Mapped[list[str]] = mapped_column(JSON, default=list)
    # named cast_members, not `cast` — avoids shadowing the `cast` builtin/typing name
    cast_members: Mapped[list[str]] = mapped_column(JSON, default=list)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String, nullable=True)
    tagline: Mapped[str | None] = mapped_column(String, nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(String, nullable=True)
    vote_average: Mapped[float | None] = mapped_column(Float, nullable=True)  # TMDb 0-10 scale
    vote_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    # No `embedding` column yet — when pgvector lands on Postgres, add one via a
    # migration using pgvector.sqlalchemy.Vector(1536); id/tmdb_id stay stable.
