from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class MovieSearchResult(BaseModel):
    """Lightweight result from a TMDb search/browse list — not yet cached to our DB."""

    tmdb_id: int
    title: str
    year: int | None
    poster_url: str | None


class MovieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tmdb_id: int
    title: str
    year: int | None
    runtime: int | None
    genres: list[str]
    directors: list[str]
    cast_members: list[str]
    overview: str | None
    poster_url: str | None
    tagline: str | None
    backdrop_url: str | None
    vote_average: float | None
    vote_count: int | None
    created_at: datetime
    updated_at: datetime


class MovieReviewOut(BaseModel):
    """A logged watch with a review, surfaced across all users on a movie's detail page."""

    model_config = ConfigDict(from_attributes=True)

    reviewer_name: str
    reviewer_picture_url: str | None
    rating: float | None
    liked: bool
    review_text: str
    watched_date: date
