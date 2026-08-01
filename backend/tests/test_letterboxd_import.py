import io
import zipfile

from sqlalchemy import select

from app.models.diary_entry import DiaryEntry
from app.models.list import ListMovie, MovieList
from app.models.watchlist import WatchlistItem

DIARY_CSV = """Date,Name,Year,Letterboxd URI,Rating,Rewatch,Tags,Watched Date
2026-07-01,Movie One,2020,https://boxd.it/1,4.5,,,2026-07-01
2026-07-02,Movie Two,2021,https://boxd.it/2,,Yes,comfort,2026-07-02
"""

RATINGS_CSV = """Date,Name,Year,Letterboxd URI,Rating
2026-06-01,Movie Three,2019,https://boxd.it/3,3.5
"""

REVIEWS_CSV = """Date,Name,Year,Letterboxd URI,Rating,Review,Tags,Watched Date
2026-07-01,Movie One,2020,https://boxd.it/1,4.5,Loved it!,,2026-07-01
"""

WATCHLIST_CSV = """Date,Name,Year,Letterboxd URI
2026-05-01,Movie Four,2022,https://boxd.it/4
"""

LIST_CSV = """Letterboxd list export
Date,Name,Description
2026-01-01,My Favorites,Films I love

Position,Name,Year,Letterboxd URI
1,Movie One,2020,https://boxd.it/1
2,Movie Five,2023,https://boxd.it/5
"""


def build_export_zip(*, include_watched=True, list_csv=LIST_CSV) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("diary.csv", DIARY_CSV)
        zf.writestr("ratings.csv", RATINGS_CSV)
        zf.writestr("reviews.csv", REVIEWS_CSV)
        zf.writestr("watchlist.csv", WATCHLIST_CSV)
        if include_watched:
            zf.writestr("watched.csv", "Date,Name,Year,Letterboxd URI\n")
        if list_csv is not None:
            zf.writestr("lists/My Favorites.csv", list_csv)
    return buffer.getvalue()


def upload(client, content: bytes, filename: str = "export.zip"):
    return client.post(
        "/api/import/letterboxd",
        files={"file": (filename, content, "application/zip")},
    )


def test_requires_auth(unauthenticated_client):
    response = upload(unauthenticated_client, build_export_zip())
    assert response.status_code == 401


def test_rejects_non_zip(client):
    response = upload(client, b"this is not a zip file", filename="export.zip")
    assert response.status_code == 400
    assert "zip" in response.json()["detail"].lower()


def test_rejects_zip_missing_expected_files(client):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("readme.txt", "hello")
    response = upload(client, buffer.getvalue())
    assert response.status_code == 400
    assert "letterboxd" in response.json()["detail"].lower()


def test_happy_path_import(client, import_db, mock_import_tmdb, db_session, test_user):
    response = upload(client, build_export_zip())
    assert response.status_code == 202
    job_id = response.json()["id"]

    # BackgroundTasks run synchronously within TestClient's request/response cycle,
    # so the job has already finished by the time this response comes back.
    status_response = client.get(f"/api/import/letterboxd/{job_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "completed"

    summary = body["summary"]
    # Movie One (diary + review merge) + Movie Two (rewatch) + Movie Three (ratings-only)
    assert summary["diary_entries_imported"] == 3
    assert summary["diary_entries_skipped"] == 0
    assert summary["watchlist_items_imported"] == 1
    assert summary["lists_imported"] == 1
    # List has 2 items but "Movie Five" doesn't resolve — only 1 actually links in.
    assert summary["list_movies_imported"] == 1
    assert summary["unmatched_films"] == [{"title": "Movie Five", "year": 2023}]

    diary_entries = db_session.scalars(
        select(DiaryEntry).where(DiaryEntry.user_email == test_user.email)
    ).all()
    assert len(diary_entries) == 3
    movie_one_entry = next(e for e in diary_entries if e.movie.tmdb_id == 101)
    assert movie_one_entry.rating == 4.5
    assert movie_one_entry.review_text == "Loved it!"
    assert movie_one_entry.source == "import"

    movie_two_entry = next(e for e in diary_entries if e.movie.tmdb_id == 102)
    assert movie_two_entry.rewatch is True
    assert movie_two_entry.tags == ["comfort"]

    watchlist_items = db_session.scalars(
        select(WatchlistItem).where(WatchlistItem.user_email == test_user.email)
    ).all()
    assert len(watchlist_items) == 1
    assert watchlist_items[0].movie.tmdb_id == 104

    movie_list = db_session.scalar(
        select(MovieList).where(MovieList.user_email == test_user.email)
    )
    assert movie_list.name == "My Favorites"
    assert movie_list.description == "Films I love"
    list_movies = db_session.scalars(
        select(ListMovie).where(ListMovie.list_id == movie_list.id)
    ).all()
    assert len(list_movies) == 1
    assert list_movies[0].movie.tmdb_id == 101


def test_rerun_dedupes_instead_of_duplicating(client, import_db, mock_import_tmdb, db_session, test_user):
    first = upload(client, build_export_zip())
    first_job = client.get(f"/api/import/letterboxd/{first.json()['id']}").json()
    assert first_job["status"] == "completed"

    second = upload(client, build_export_zip())
    second_job = client.get(f"/api/import/letterboxd/{second.json()['id']}").json()
    assert second_job["status"] == "completed"

    second_summary = second_job["summary"]
    assert second_summary["diary_entries_imported"] == 0
    assert second_summary["diary_entries_skipped"] == 3
    assert second_summary["watchlist_items_imported"] == 0
    assert second_summary["watchlist_items_skipped"] == 1

    diary_entries = db_session.scalars(
        select(DiaryEntry).where(DiaryEntry.user_email == test_user.email)
    ).all()
    assert len(diary_entries) == 3  # not 6 — the rerun didn't create duplicates

    watchlist_items = db_session.scalars(
        select(WatchlistItem).where(WatchlistItem.user_email == test_user.email)
    ).all()
    assert len(watchlist_items) == 1

    # The list should be reused (matched by name), not duplicated.
    lists = db_session.scalars(select(MovieList).where(MovieList.user_email == test_user.email)).all()
    assert len(lists) == 1
