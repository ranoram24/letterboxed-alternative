import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.movie import Movie
from app.models.user import User
from app.schemas.movie import MovieSearchResult


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = testing_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def test_user(db_session):
    user = User(
        email="test@example.com",
        google_sub="google-sub-123",
        display_name="Test User",
        profile_picture_url="https://example.com/pic.jpg",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def mock_tmdb(monkeypatch):
    """Stand in for real TMDb calls so tests don't need network access or an API key."""

    async def fake_get_or_cache_movie(db, tmdb_id, settings=None):
        movie = db.scalar(select(Movie).where(Movie.tmdb_id == tmdb_id))
        if movie is not None:
            return movie
        movie = Movie(
            tmdb_id=tmdb_id,
            title=f"Test Movie {tmdb_id}",
            year=2020,
            runtime=100,
            genres=["Drama"],
            directors=["Test Director"],
            cast_members=["Test Actor"],
            overview="A test movie.",
            poster_url=None,
        )
        db.add(movie)
        db.flush()
        return movie

    async def fake_search_movies(query, settings=None):
        return [MovieSearchResult(tmdb_id=999, title="Search Result", year=2021, poster_url=None)]

    async def fake_get_popular_movies(settings=None):
        return [
            MovieSearchResult(
                tmdb_id=1, title="Popular Movie 1", year=2024, poster_url="https://image.tmdb.org/t/p/w500/1.jpg"
            ),
            MovieSearchResult(
                tmdb_id=2, title="Popular Movie 2", year=2023, poster_url="https://image.tmdb.org/t/p/w500/2.jpg"
            ),
        ]

    async def fake_get_now_playing_movies(settings=None):
        return [
            MovieSearchResult(
                tmdb_id=3, title="New Release 1", year=2026, poster_url="https://image.tmdb.org/t/p/w500/3.jpg"
            ),
        ]

    monkeypatch.setattr("app.api.routers.movies.get_or_cache_movie", fake_get_or_cache_movie)
    monkeypatch.setattr("app.api.routers.movies.search_movies", fake_search_movies)
    monkeypatch.setattr("app.api.routers.movies.get_popular_movies", fake_get_popular_movies)
    monkeypatch.setattr("app.api.routers.movies.get_now_playing_movies", fake_get_now_playing_movies)
    monkeypatch.setattr("app.api.routers.library.get_or_cache_movie", fake_get_or_cache_movie)


@pytest.fixture()
def claude_responses(monkeypatch):
    """Queue of MovieChoiceLLM|None to return from successive _call_claude calls, so
    tests don't need a real Anthropic API key or network access."""
    from app.services import what_to_choose as what_to_choose_module

    responses: list = []

    def fake_call_claude(system_prompt):
        return responses.pop(0) if responses else None

    monkeypatch.setattr(what_to_choose_module, "_call_claude", fake_call_claude)
    return responses


@pytest.fixture()
def mock_discover(monkeypatch):
    """Stand in for TMDb's /discover/movie call used by AI recommendations."""

    async def fake_discover_movies_by_genre(genre_ids, exclude_tmdb_ids, settings=None, pages=(1, 2, 3)):
        candidates = [
            {
                "movie_id": 501,
                "title": "Discover Movie 1",
                "year": 2022,
                "genres": ["Drama"],
                "overview": "A discovered movie.",
                "popularity": 50.0,
                "vote_average": 7.5,
                "poster_url": "https://image.tmdb.org/t/p/w500/501.jpg",
            },
            {
                "movie_id": 502,
                "title": "Discover Movie 2",
                "year": 2023,
                "genres": ["Drama"],
                "overview": "Another discovered movie.",
                "popularity": 40.0,
                "vote_average": 7.0,
                "poster_url": "https://image.tmdb.org/t/p/w500/502.jpg",
            },
        ]
        return [candidate for candidate in candidates if candidate["movie_id"] not in exclude_tmdb_ids]

    monkeypatch.setattr("app.services.recommendations.discover_movies_by_genre", fake_discover_movies_by_genre)


@pytest.fixture()
def recommendation_responses(monkeypatch):
    """Queue of RecommendationsLLM|None to return from successive _call_claude calls, so
    tests don't need a real Anthropic API key or network access."""
    from app.services import recommendations as recommendations_module

    responses: list = []

    def fake_call_claude(system_prompt):
        return responses.pop(0) if responses else None

    monkeypatch.setattr(recommendations_module, "_call_claude", fake_call_claude)
    return responses


@pytest.fixture()
def import_db(monkeypatch, db_session):
    """The background import job opens its own DB session (it runs after the request's
    session is closed) — point it at the same in-memory engine as db_session so tests
    can see what the job wrote."""
    test_session_local = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr("app.services.letterboxd_import.SessionLocal", test_session_local)


@pytest.fixture()
def mock_import_tmdb(monkeypatch):
    """Stand in for TMDb title/year matching used by the Letterboxd import job."""

    async def fake_find_best_match(title, year, settings=None):
        tmdb_id = MOVIE_TITLE_TO_TMDB_ID.get(title.lower())
        if tmdb_id is None:
            return None
        return MovieSearchResult(tmdb_id=tmdb_id, title=title, year=year, poster_url=None)

    async def fake_get_or_cache_movie(db, tmdb_id, settings=None):
        movie = db.scalar(select(Movie).where(Movie.tmdb_id == tmdb_id))
        if movie is not None:
            return movie
        movie = Movie(tmdb_id=tmdb_id, title=f"Movie {tmdb_id}", year=2020)
        db.add(movie)
        db.flush()
        return movie

    monkeypatch.setattr("app.services.letterboxd_import.find_best_match", fake_find_best_match)
    monkeypatch.setattr("app.services.letterboxd_import.get_or_cache_movie", fake_get_or_cache_movie)


# Title (lowercase) -> tmdb_id used by mock_import_tmdb; "movie five" is deliberately
# absent so tests can exercise the unmatched-film path.
MOVIE_TITLE_TO_TMDB_ID = {
    "movie one": 101,
    "movie two": 102,
    "movie three": 103,
    "movie four": 104,
}


@pytest.fixture()
def client(db_session, test_user, mock_tmdb):
    def override_get_db():
        yield db_session

    def override_get_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def unauthenticated_client(db_session, mock_tmdb):
    """A client with the DB overridden but no current-user override, to verify 401s."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
