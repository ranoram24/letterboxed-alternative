from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MovieList(Base):
    __tablename__ = "lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_email: Mapped[str] = mapped_column(ForeignKey("users.email"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="lists")
    items: Mapped[list["ListMovie"]] = relationship(
        back_populates="movie_list",
        cascade="all, delete-orphan",
        order_by="ListMovie.position",
    )


class ListMovie(Base):
    __tablename__ = "lists_movies"

    list_id: Mapped[int] = mapped_column(ForeignKey("lists.id"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    movie_list: Mapped["MovieList"] = relationship(back_populates="items")
    movie: Mapped["Movie"] = relationship()
