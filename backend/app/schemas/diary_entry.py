from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.movie import MovieOut


class DiaryEntryCreate(BaseModel):
    tmdb_id: int
    watched_date: date
    rating: float | None = None
    rewatch: bool = False
    review_text: str | None = None
    tags: list[str] = []
    liked: bool = False


class DiaryEntryUpdate(BaseModel):
    watched_date: date | None = None
    rating: float | None = None
    rewatch: bool | None = None
    review_text: str | None = None
    tags: list[str] | None = None
    liked: bool | None = None


class DiaryEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie: MovieOut
    watched_date: date
    rating: float | None
    rewatch: bool
    review_text: str | None
    tags: list[str]
    liked: bool
    source: str
    created_at: datetime
    updated_at: datetime
