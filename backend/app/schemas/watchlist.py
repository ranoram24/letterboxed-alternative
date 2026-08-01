from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.movie import MovieOut


class WatchlistItemCreate(BaseModel):
    tmdb_id: int


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie: MovieOut
    added_date: datetime
