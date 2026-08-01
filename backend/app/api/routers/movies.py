from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.diary_entry import DiaryEntry
from app.models.movie import Movie
from app.models.user import User
from app.schemas.movie import MovieOut, MovieReviewOut, MovieSearchResult
from app.schemas.recommendation import RecommendedMovieOut
from app.services.recommendations import get_recommendations_cached
from app.services.tmdb_client import (
    get_now_playing_movies,
    get_or_cache_movie,
    get_popular_movies,
    search_movies,
)

router = APIRouter(prefix="/api/movies", tags=["movies"])


@router.get("/search", response_model=list[MovieSearchResult])
async def search(q: str, current_user: User = Depends(get_current_user)):
    return await search_movies(q)


@router.get("/popular", response_model=list[MovieSearchResult])
async def popular():
    """Public/unauthenticated — used for the pre-login backdrop and the home dashboard."""
    return await get_popular_movies()


@router.get("/now-playing", response_model=list[MovieSearchResult])
async def now_playing():
    """Public/unauthenticated, same reasoning as /popular."""
    return await get_now_playing_movies()


@router.get("/recommendations", response_model=list[RecommendedMovieOut])
async def recommendations(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """AI-personalized picks — returns [] until the user has rated diary entries to base
    taste on; the frontend hides the whole "Recommended for You" row in that case.
    Cached per-user for 24h — see get_recommendations_cached."""
    return await get_recommendations_cached(db, current_user)


@router.get("/{tmdb_id}", response_model=MovieOut)
async def get_movie(
    tmdb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie = await get_or_cache_movie(db, tmdb_id)
    db.commit()
    return movie


@router.get("/{tmdb_id}/reviews", response_model=list[MovieReviewOut])
def get_reviews(
    tmdb_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reviews from Movie Explorer members who've logged this movie — deliberately cross-user
    (unlike /api/library, which is always scoped to the caller)."""
    stmt = (
        select(DiaryEntry)
        .join(Movie, DiaryEntry.movie_id == Movie.id)
        .join(User, DiaryEntry.user_email == User.email)
        .where(Movie.tmdb_id == tmdb_id, DiaryEntry.review_text.is_not(None))
        .order_by(DiaryEntry.created_at.desc())
        .limit(50)
    )
    entries = db.scalars(stmt).all()

    return [
        MovieReviewOut(
            reviewer_name=entry.user.display_name,
            reviewer_picture_url=entry.user.profile_picture_url,
            rating=entry.rating,
            liked=entry.liked,
            review_text=entry.review_text,
            watched_date=entry.watched_date,
        )
        for entry in entries
    ]
