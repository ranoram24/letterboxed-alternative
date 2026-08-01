import random
from datetime import datetime
from functools import lru_cache

import anthropic
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.diary_entry import DiaryEntry
from app.models.movie import Movie
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.schemas.what_to_choose import WhatToChooseRequest

CLAUDE_MODEL = "claude-sonnet-5"


class MovieChoiceLLM(BaseModel):
    """Structured output schema Claude must fill — validated by the SDK's response parser."""

    movie_id: int
    reason: str


@lru_cache
def _get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)


def _time_of_day_label(local_datetime: str) -> str:
    try:
        parsed = datetime.fromisoformat(local_datetime)
    except ValueError:
        return "unspecified"

    hour = parsed.hour
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "late night"


def _build_candidates(db: Session, user_email: str) -> list[dict]:
    stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.user_email == user_email)
        .order_by(WatchlistItem.added_date.asc())
    )
    items = db.scalars(stmt).all()

    return [
        {
            "movie_id": item.movie.id,
            "title": item.movie.title,
            "year": item.movie.year,
            "genres": item.movie.genres,
            "runtime": item.movie.runtime,
            "directors": item.movie.directors,
            "top_cast": item.movie.cast_members[:5],
            "overview": item.movie.overview,
            "tmdb_popularity": item.movie.popularity,
            "added_to_watchlist": item.added_date.date().isoformat(),
        }
        for item in items
    ]


def _genre_distribution(candidates: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for candidate in candidates:
        for genre in candidate["genres"]:
            counts[genre] = counts.get(genre, 0) + 1
    return dict(sorted(counts.items(), key=lambda pair: pair[1], reverse=True))


def compute_taste_summary(db: Session, user_email: str) -> dict:
    """Top-rated genres/directors + average rating per genre, derived from diary_entries.

    Computed here in Python rather than left for the model to tally from raw rows.
    """
    stmt = (
        select(DiaryEntry)
        .where(DiaryEntry.user_email == user_email, DiaryEntry.rating.is_not(None))
    )
    entries = db.scalars(stmt).all()

    if not entries:
        return {"total_rated": 0, "top_genres": [], "top_directors": []}

    genre_ratings: dict[str, list[float]] = {}
    director_ratings: dict[str, list[float]] = {}
    for entry in entries:
        for genre in entry.movie.genres:
            genre_ratings.setdefault(genre, []).append(entry.rating)
        for director in entry.movie.directors:
            director_ratings.setdefault(director, []).append(entry.rating)

    def _top(ratings_by_key: dict[str, list[float]], limit: int = 5) -> list[dict]:
        summarized = [
            {"name": key, "avg_rating": round(sum(values) / len(values), 2), "count": len(values)}
            for key, values in ratings_by_key.items()
        ]
        summarized.sort(key=lambda entry: entry["avg_rating"], reverse=True)
        return summarized[:limit]

    return {
        "total_rated": len(entries),
        "top_genres": _top(genre_ratings),
        "top_directors": _top(director_ratings),
    }


def _build_system_prompt(candidates: list[dict], genre_distribution: dict, taste_summary: dict, time_label: str) -> str:
    return f"""You are helping a user of a movie-tracking app decide what to watch right now, from their watchlist only.

## Their taste, derived from movies they've already rated
{taste_summary}
(If total_rated is 0, they have no rating history yet — treat all candidates as equally unknown on taste fit.)

## Genre distribution across their whole watchlist (counts)
{genre_distribution}

## Time of day right now (their local time): {time_label}

## Their watchlist — the ONLY movies you may choose from
Each entry includes its movie_id, metadata, and TMDb's popularity score.
{candidates}

## How to decide
- Taste fit (from their rating history above) is the PRIMARY factor.
- TMDb popularity is only a light tiebreaker between otherwise similar options — never the deciding factor on its own.
- Time of day is a mood/intensity filter, not a hard rule: e.g. lean away from very heavy, dense, or long films late at night, but don't treat this as an absolute exclusion — a great fit on taste can still win at any hour.
- You MUST pick exactly one movie_id from the watchlist above. Never suggest a movie that isn't in that list.
- Write a 2-3 sentence reason for your pick that references their taste and/or the moment (time of day), in a friendly, direct tone — as if a friend who knows their taste was making the call.
"""


def _call_claude(system_prompt: str) -> MovieChoiceLLM | None:
    try:
        response = _get_client().messages.parse(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": "Choose one movie for me to watch right now."}],
            output_format=MovieChoiceLLM,
        )
    except anthropic.APIError:
        return None

    return response.parsed_output


def choose_movie(db: Session, user: User, request: WhatToChooseRequest) -> tuple[Movie, str]:
    """Pick one movie from the user's watchlist via a single Claude call.

    Validates the model's pick against the actual watchlist, retries once on a bad
    pick, then falls back to a random watchlist choice rather than failing the request.
    """
    candidates = _build_candidates(db, user.email)
    if not candidates:
        raise ValueError("watchlist is empty")

    candidates_by_id = {candidate["movie_id"]: candidate for candidate in candidates}

    genre_distribution = _genre_distribution(candidates)
    taste_summary = compute_taste_summary(db, user.email)
    time_label = _time_of_day_label(request.local_datetime)
    system_prompt = _build_system_prompt(candidates, genre_distribution, taste_summary, time_label)

    for _attempt in range(2):
        choice = _call_claude(system_prompt)
        if choice is not None and choice.movie_id in candidates_by_id:
            movie = db.get(Movie, choice.movie_id)
            assert movie is not None
            return movie, choice.reason

    fallback_id = random.choice(list(candidates_by_id))
    fallback_movie = db.get(Movie, fallback_id)
    assert fallback_movie is not None
    return fallback_movie, "Picked at random from your watchlist since we couldn't get a confident recommendation this time."
