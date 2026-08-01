from datetime import datetime, timedelta

import anthropic
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.diary_entry import DiaryEntry
from app.models.movie import Movie
from app.models.recommendation_cache import RecommendationCache
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.schemas.movie import MovieSearchResult
from app.schemas.recommendation import RecommendedMovieOut
from app.services.tmdb_client import GENRE_NAME_TO_ID, discover_movies_by_genre
from app.services.what_to_choose import CLAUDE_MODEL, _get_client, compute_taste_summary

RECOMMENDATION_COUNT = 10
TOP_GENRE_COUNT = 4
CACHE_TTL = timedelta(hours=24)


class RecommendedPick(BaseModel):
    movie_id: int
    reason: str


class RecommendationsLLM(BaseModel):
    """Structured output schema Claude must fill — validated by the SDK's response parser."""

    recommendations: list[RecommendedPick]


def _watchlist_genre_distribution(db: Session, user_email: str) -> dict[str, int]:
    stmt = select(WatchlistItem).where(WatchlistItem.user_email == user_email)
    items = db.scalars(stmt).all()

    counts: dict[str, int] = {}
    for item in items:
        for genre in item.movie.genres:
            counts[genre] = counts.get(genre, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: pair[1], reverse=True))


def _seen_tmdb_ids(db: Session, user_email: str) -> set[int]:
    """Movies already watched or queued — never worth recommending again."""
    diary_ids = db.scalars(
        select(Movie.tmdb_id)
        .join(DiaryEntry, DiaryEntry.movie_id == Movie.id)
        .where(DiaryEntry.user_email == user_email)
    ).all()
    watchlist_ids = db.scalars(
        select(Movie.tmdb_id)
        .join(WatchlistItem, WatchlistItem.movie_id == Movie.id)
        .where(WatchlistItem.user_email == user_email)
    ).all()
    return set(diary_ids) | set(watchlist_ids)


def _top_genre_ids(taste_summary: dict, watchlist_genres: dict[str, int], limit: int = TOP_GENRE_COUNT) -> list[int]:
    """Blend rated-diary taste (primary signal) with watchlist genre counts (lighter weight)
    into a single ranked genre list, then map to TMDb's genre ids for the discover query."""
    scores: dict[str, float] = {}
    for entry in taste_summary.get("top_genres", []):
        scores[entry["name"]] = scores.get(entry["name"], 0) + entry["avg_rating"] * entry["count"]
    for genre, count in watchlist_genres.items():
        scores[genre] = scores.get(genre, 0) + count

    ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)

    genre_ids: list[int] = []
    for name, _score in ranked:
        genre_id = GENRE_NAME_TO_ID.get(name)
        if genre_id is not None and genre_id not in genre_ids:
            genre_ids.append(genre_id)
        if len(genre_ids) >= limit:
            break
    return genre_ids


def _build_system_prompt(taste_summary: dict, watchlist_genres: dict, candidates: list[dict]) -> str:
    return f"""You are helping a user of a movie-tracking app discover new movies to watch, personalized to their taste.

## Their taste, derived from movies they've already rated
{taste_summary}

## Genre distribution across their current watchlist (counts)
{watchlist_genres}

## Candidate movies — you may ONLY recommend from this list
None of these are in their diary or watchlist already. Each includes its movie_id, metadata, and TMDb's popularity/rating.
{candidates}

## How to decide
- Taste fit (from their rating history and watchlist genres above) is the PRIMARY factor — favor genres, and directors/styles implied by what they've loved.
- TMDb popularity and vote_average are light tiebreakers, never the deciding factor on their own — don't just return the most popular movies.
- Pick up to {RECOMMENDATION_COUNT} of the strongest matches from the candidate list, ranked best-first. You may return fewer if the pool doesn't have that many good fits — never pad with weak matches.
- Only use movie_id values that appear in the candidate list above. Never invent one.
- Write a short one-sentence reason for each pick.
"""


def _call_claude(system_prompt: str) -> RecommendationsLLM | None:
    try:
        response = _get_client().messages.parse(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"Recommend up to {RECOMMENDATION_COUNT} movies for me from the candidates above.",
                }
            ],
            output_format=RecommendationsLLM,
        )
    except anthropic.APIError:
        return None

    return response.parsed_output


async def get_recommendations(db: Session, user: User) -> list[RecommendedMovieOut]:
    """AI-personalized movie recommendations, or an empty list if there isn't enough
    signal yet (brand-new users with no rated diary entries) — the frontend hides the
    whole row in that case rather than showing an empty/generic one.
    """
    taste_summary = compute_taste_summary(db, user.email)
    if taste_summary["total_rated"] == 0:
        return []

    watchlist_genres = _watchlist_genre_distribution(db, user.email)
    genre_ids = _top_genre_ids(taste_summary, watchlist_genres)
    if not genre_ids:
        return []

    excluded = _seen_tmdb_ids(db, user.email)
    candidates = await discover_movies_by_genre(genre_ids, excluded)
    if not candidates:
        return []

    candidates_by_id = {candidate["movie_id"]: candidate for candidate in candidates}
    system_prompt = _build_system_prompt(taste_summary, watchlist_genres, candidates)

    result = _call_claude(system_prompt)
    picks = result.recommendations if result is not None else []

    recommendations: list[RecommendedMovieOut] = []
    seen_picks: set[int] = set()
    for pick in picks:
        if pick.movie_id in seen_picks:
            continue
        candidate = candidates_by_id.get(pick.movie_id)
        if candidate is None:
            continue
        seen_picks.add(pick.movie_id)
        recommendations.append(
            RecommendedMovieOut(
                movie=MovieSearchResult(
                    tmdb_id=candidate["movie_id"],
                    title=candidate["title"],
                    year=candidate["year"],
                    poster_url=candidate["poster_url"],
                ),
                reason=pick.reason,
            )
        )
        if len(recommendations) >= RECOMMENDATION_COUNT:
            break

    return recommendations


async def get_recommendations_cached(db: Session, user: User) -> list[RecommendedMovieOut]:
    """Same as get_recommendations, but only recomputes (a Claude + TMDb round trip) once
    per CACHE_TTL per user — every other home page load in that window reads the cached
    row instead, keeping this both cheap and fast to load.
    """
    cache_row = db.get(RecommendationCache, user.email)
    if cache_row is not None and datetime.utcnow() - cache_row.computed_at < CACHE_TTL:
        return [RecommendedMovieOut.model_validate(item) for item in cache_row.payload]

    recommendations = await get_recommendations(db, user)

    # Don't cache empty results — that path is already instant (no signal yet, or a
    # transient Claude/TMDb failure), and caching it would either lock a brand-new user
    # out of ever seeing the row for a day, or paper over a one-off failure for just as long.
    if recommendations:
        payload = [item.model_dump(mode="json") for item in recommendations]
        if cache_row is None:
            db.add(RecommendationCache(user_email=user.email, payload=payload))
        else:
            cache_row.payload = payload
            cache_row.computed_at = datetime.utcnow()
        db.commit()

    return recommendations
