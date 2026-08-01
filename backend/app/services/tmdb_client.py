import asyncio

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.movie import Movie
from app.schemas.movie import MovieSearchResult

TMDB_POSTER_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"


def _poster_url(poster_path: str | None) -> str | None:
    return f"{TMDB_POSTER_BASE}{poster_path}" if poster_path else None


def _backdrop_url(backdrop_path: str | None) -> str | None:
    return f"{TMDB_BACKDROP_BASE}{backdrop_path}" if backdrop_path else None


async def search_movies(query: str, settings: Settings | None = None) -> list[MovieSearchResult]:
    settings = settings or get_settings()
    async with httpx.AsyncClient(base_url=settings.tmdb_api_base_url) as client:
        response = await client.get(
            "/search/movie",
            params={"api_key": settings.tmdb_api_key, "query": query},
        )
        response.raise_for_status()
        results = response.json().get("results", [])

    return [
        MovieSearchResult(
            tmdb_id=result["id"],
            title=result["title"],
            year=int(result["release_date"][:4]) if result.get("release_date") else None,
            poster_url=_poster_url(result.get("poster_path")),
        )
        for result in results
    ]


async def _fetch_movie_list(
    tmdb_path: str, settings: Settings, pages: tuple[int, ...] = (1, 2)
) -> list[MovieSearchResult]:
    """Shared fetcher for TMDb's curated list endpoints (popular, now_playing, ...).

    Used for browsing/discovery sections — no auth/session required by these endpoints,
    since they're the same kind of public catalog browsing TMDb itself exposes.
    """
    async with httpx.AsyncClient(base_url=settings.tmdb_api_base_url) as client:
        responses = await asyncio.gather(
            *[
                client.get(tmdb_path, params={"api_key": settings.tmdb_api_key, "page": page})
                for page in pages
            ]
        )

    movies: list[MovieSearchResult] = []
    seen_tmdb_ids: set[int] = set()
    for response in responses:
        response.raise_for_status()
        for result in response.json().get("results", []):
            poster_url = _poster_url(result.get("poster_path"))
            if poster_url is None or result["id"] in seen_tmdb_ids:
                # Skip missing posters and cross-page duplicates — TMDb's list can shift
                # between our two concurrent page requests and repeat an entry.
                continue
            seen_tmdb_ids.add(result["id"])
            movies.append(
                MovieSearchResult(
                    tmdb_id=result["id"],
                    title=result["title"],
                    year=int(result["release_date"][:4]) if result.get("release_date") else None,
                    poster_url=poster_url,
                )
            )

    return movies


async def get_popular_movies(settings: Settings | None = None) -> list[MovieSearchResult]:
    return await _fetch_movie_list("/movie/popular", settings or get_settings())


async def get_now_playing_movies(settings: Settings | None = None) -> list[MovieSearchResult]:
    return await _fetch_movie_list("/movie/now_playing", settings or get_settings())


async def _fetch_movie_detail(tmdb_id: int, settings: Settings) -> dict:
    async with httpx.AsyncClient(base_url=settings.tmdb_api_base_url) as client:
        response = await client.get(
            f"/movie/{tmdb_id}",
            params={"api_key": settings.tmdb_api_key, "append_to_response": "credits"},
        )
        response.raise_for_status()
        return response.json()


def _normalize_detail(data: dict) -> dict:
    credits = data.get("credits", {})
    directors = [c["name"] for c in credits.get("crew", []) if c.get("job") == "Director"]
    cast_members = [c["name"] for c in credits.get("cast", [])[:20]]

    return {
        "title": data["title"],
        "year": int(data["release_date"][:4]) if data.get("release_date") else None,
        "runtime": data.get("runtime"),
        "genres": [g["name"] for g in data.get("genres", [])],
        "directors": directors,
        "cast_members": cast_members,
        "overview": data.get("overview"),
        "poster_url": _poster_url(data.get("poster_path")),
        "tagline": data.get("tagline") or None,
        "backdrop_url": _backdrop_url(data.get("backdrop_path")),
        "vote_average": data.get("vote_average"),
        "vote_count": data.get("vote_count"),
        "popularity": data.get("popularity"),
    }


async def get_or_cache_movie(db: Session, tmdb_id: int, settings: Settings | None = None) -> Movie:
    """Return the locally-cached Movie row for a TMDb id, fetching + caching it first if needed.

    Diary/watchlist/list rows FK to this local `movie.id` (not `tmdb_id` directly) so they
    stay stable even if TMDb metadata is later refreshed.
    """
    settings = settings or get_settings()

    movie = db.scalar(select(Movie).where(Movie.tmdb_id == tmdb_id))
    # vote_average is always a float (0.0 if unrated) once fetched via this path, so `None`
    # only ever means "cached before the detail-page fields existed" — a one-time backfill.
    if movie is not None and movie.vote_average is not None:
        return movie

    detail = await _fetch_movie_detail(tmdb_id, settings)
    normalized = _normalize_detail(detail)

    if movie is None:
        movie = Movie(tmdb_id=tmdb_id, **normalized)
        db.add(movie)
    else:
        # Backfill rows cached before the detail-page fields (tagline, rating, backdrop) existed.
        for field, value in normalized.items():
            setattr(movie, field, value)

    db.flush()
    return movie
