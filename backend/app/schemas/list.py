from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.movie import MovieOut


class MovieListCreate(BaseModel):
    name: str
    description: str | None = None


class MovieListUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ListMovieAdd(BaseModel):
    tmdb_id: int


class ListMovieReorder(BaseModel):
    movie_ids: list[int]


class ListMovieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movie: MovieOut
    position: int


class MovieListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class MovieListDetailOut(MovieListOut):
    items: list[ListMovieOut]
