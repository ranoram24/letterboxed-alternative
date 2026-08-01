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
