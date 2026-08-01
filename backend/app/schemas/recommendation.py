from pydantic import BaseModel

from app.schemas.movie import MovieSearchResult


class RecommendedMovieOut(BaseModel):
    movie: MovieSearchResult
    reason: str
