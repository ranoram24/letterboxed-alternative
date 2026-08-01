import asyncio
import csv
import io
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select

from app.config import Settings, get_settings
from app.database import SessionLocal
from app.models.diary_entry import DiaryEntry
from app.models.import_job import ImportJob
from app.models.list import ListMovie, MovieList
from app.models.movie import Movie
from app.models.watchlist import WatchlistItem
from app.services.tmdb_client import find_best_match, get_or_cache_movie

EXPECTED_FILENAMES = {"diary.csv", "ratings.csv", "watched.csv"}
MovieKey = tuple[str, int | None]


def validate_export_zip(file_bytes: bytes) -> None:
    """Cheap, synchronous sanity check run before a job is even created.

    Raises ValueError with a message safe to show the user.
    """
    if not zipfile.is_zipfile(io.BytesIO(file_bytes)):
        raise ValueError("That file isn't a valid zip archive.")

    with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
        names = {name.rsplit("/", 1)[-1].lower() for name in zf.namelist()}
        if not (names & EXPECTED_FILENAMES):
            raise ValueError(
                "This doesn't look like a Letterboxd export — expected files like diary.csv "
                "or ratings.csv weren't found in the zip."
            )


# ---------------------------------------------------------------------------
# CSV parsing helpers — defensive about exact column names, since Letterboxd's
# export format has drifted across versions and isn't formally documented.
# ---------------------------------------------------------------------------


def _normalize_row(row: dict) -> dict:
    return {key.strip().lower(): (value or "").strip() for key, value in row.items() if key}


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_rating(raw: str | None) -> float | None:
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_year(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _find_member(zf: zipfile.ZipFile, filename: str) -> str | None:
    filename = filename.lower()
    for name in zf.namelist():
        if name.rsplit("/", 1)[-1].lower() == filename:
            return name
    return None


def _read_csv(zf: zipfile.ZipFile, filename: str) -> list[dict] | None:
    member = _find_member(zf, filename)
    if member is None:
        return None
    with zf.open(member) as handle:
        text = handle.read().decode("utf-8-sig")
    return [_normalize_row(row) for row in csv.DictReader(io.StringIO(text))]


def _find_list_members(zf: zipfile.ZipFile) -> list[str]:
    return [
        name
        for name in zf.namelist()
        if "lists/" in name.lower() and name.lower().endswith(".csv")
    ]


def _parse_list_csv(text: str) -> dict | None:
    """Letterboxd list exports aren't a plain single-header CSV: line 2 is a metadata
    header row, line 3 its values (list name/description), a blank line, then the
    film rows starting at line 5 (0-indexed: lines[1], lines[2], lines[4]...)."""
    lines = text.lstrip("﻿").splitlines()
    if len(lines) < 5:
        return None

    meta_headers = next(csv.reader([lines[1]]))
    meta_values = next(csv.reader([lines[2]]))
    metadata = {h.strip().lower(): v for h, v in zip(meta_headers, meta_values)}

    item_headers = [h.strip().lower() for h in next(csv.reader([lines[4]]))]
    items = []
    for line in lines[5:]:
        if not line.strip():
            continue
        values = next(csv.reader([line]))
        if len(values) != len(item_headers):
            continue
        items.append(dict(zip(item_headers, values)))

    return {
        "name": metadata.get("name") or "Untitled List",
        "description": metadata.get("description") or None,
        "items": items,
    }


def _item_title_year(item: dict) -> tuple[str, int | None]:
    title = (item.get("name") or item.get("film name") or item.get("title") or "").strip()
    year = _parse_year(item.get("year") or item.get("release year"))
    return title, year


# ---------------------------------------------------------------------------
# diary.csv + ratings.csv + reviews.csv merge
# ---------------------------------------------------------------------------


@dataclass
class DiaryCandidate:
    title: str
    year: int | None
    watched_date: date | None
    rating: float | None
    rewatch: bool
    tags: list[str] = field(default_factory=list)
    review_text: str | None = None


def _build_diary_candidates(
    diary_rows: list[dict] | None,
    ratings_rows: list[dict] | None,
    review_rows: list[dict] | None,
) -> list[DiaryCandidate]:
    candidates: list[DiaryCandidate] = []
    covered: set[MovieKey] = set()

    for row in diary_rows or []:
        title = row.get("name", "").strip()
        if not title:
            continue
        year = _parse_year(row.get("year"))
        candidates.append(
            DiaryCandidate(
                title=title,
                year=year,
                watched_date=_parse_date(row.get("watched date") or row.get("date")),
                rating=_parse_rating(row.get("rating")),
                rewatch=(row.get("rewatch") or "").lower() == "yes",
                tags=[t.strip() for t in (row.get("tags") or "").split(",") if t.strip()],
            )
        )
        covered.add((title.lower(), year))

    # ratings.csv covers films rated without a diary log entry — only add what diary.csv
    # didn't already cover, since diary.csv is the richer source when both exist.
    for row in ratings_rows or []:
        title = row.get("name", "").strip()
        if not title:
            continue
        year = _parse_year(row.get("year"))
        key = (title.lower(), year)
        if key in covered:
            continue
        candidates.append(
            DiaryCandidate(
                title=title,
                year=year,
                watched_date=_parse_date(row.get("date")),
                rating=_parse_rating(row.get("rating")),
                rewatch=False,
            )
        )
        covered.add(key)

    by_key: dict[MovieKey, list[DiaryCandidate]] = {}
    for candidate in candidates:
        by_key.setdefault((candidate.title.lower(), candidate.year), []).append(candidate)

    # Letterboxd splits review text into its own file — merge it back onto the matching
    # diary/rating entry (preferring an exact date match for films logged more than once).
    for row in review_rows or []:
        title = row.get("name", "").strip()
        review_text = (row.get("review") or "").strip()
        if not title or not review_text:
            continue
        year = _parse_year(row.get("year"))
        review_date = _parse_date(row.get("watched date") or row.get("date"))
        key = (title.lower(), year)

        matches = by_key.get(key, [])
        target = None
        if review_date is not None:
            target = next((c for c in matches if c.watched_date == review_date), None)
        if target is None and matches:
            target = matches[-1]

        if target is not None:
            target.review_text = review_text
        else:
            # Reviewed but never appeared in diary.csv/ratings.csv — keep it rather than drop it.
            new_candidate = DiaryCandidate(
                title=title,
                year=year,
                watched_date=review_date,
                rating=_parse_rating(row.get("rating")),
                rewatch=False,
                review_text=review_text,
            )
            candidates.append(new_candidate)
            by_key.setdefault(key, []).append(new_candidate)

    return candidates


# ---------------------------------------------------------------------------
# Job execution
# ---------------------------------------------------------------------------


async def _resolve_movie(db, title: str, year: int | None, settings: Settings) -> Movie | None:
    match = await find_best_match(title, year, settings)
    if match is None:
        return None
    return await get_or_cache_movie(db, match.tmdb_id, settings)


async def _run_import_job_async(job_id: int, zip_bytes: bytes) -> None:
    db = SessionLocal()
    try:
        job = db.get(ImportJob, job_id)
        if job is None:
            return
        user_email = job.user_email

        job.status = "processing"
        db.commit()

        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))

        diary_candidates = _build_diary_candidates(
            _read_csv(zf, "diary.csv"), _read_csv(zf, "ratings.csv"), _read_csv(zf, "reviews.csv")
        )
        watchlist_rows = _read_csv(zf, "watchlist.csv") or []

        parsed_lists = []
        for member in _find_list_members(zf):
            with zf.open(member) as handle:
                text = handle.read().decode("utf-8-sig")
            parsed = _parse_list_csv(text)
            if parsed is not None:
                parsed_lists.append(parsed)

        # Every unique film across all sources — resolved against TMDb exactly once each.
        unique_titles: dict[MovieKey, str] = {}
        for candidate in diary_candidates:
            unique_titles[(candidate.title.lower(), candidate.year)] = candidate.title
        for row in watchlist_rows:
            title = row.get("name", "").strip()
            if title:
                unique_titles[(title.lower(), _parse_year(row.get("year")))] = title
        for parsed_list in parsed_lists:
            for item in parsed_list["items"]:
                title, year = _item_title_year(item)
                if title:
                    unique_titles[(title.lower(), year)] = title

        job.total_films = len(unique_titles)
        db.commit()

        settings = get_settings()
        movie_cache: dict[MovieKey, Movie | None] = {}
        unmatched: set[MovieKey] = set()

        for index, (key, title) in enumerate(unique_titles.items(), start=1):
            movie_cache[key] = await _resolve_movie(db, title, key[1], settings)
            if movie_cache[key] is None:
                unmatched.add(key)
            job.processed_films = index
            db.commit()

        diary_imported = 0
        diary_skipped = 0
        for candidate in diary_candidates:
            if candidate.watched_date is None:
                diary_skipped += 1
                continue
            movie = movie_cache.get((candidate.title.lower(), candidate.year))
            if movie is None:
                continue

            existing = db.scalar(
                select(DiaryEntry).where(
                    DiaryEntry.user_email == user_email,
                    DiaryEntry.movie_id == movie.id,
                    DiaryEntry.watched_date == candidate.watched_date,
                )
            )
            if existing is not None:
                diary_skipped += 1
                continue

            db.add(
                DiaryEntry(
                    user_email=user_email,
                    movie_id=movie.id,
                    watched_date=candidate.watched_date,
                    rating=candidate.rating,
                    rewatch=candidate.rewatch,
                    review_text=candidate.review_text,
                    tags=candidate.tags,
                    liked=False,
                    source="import",
                )
            )
            diary_imported += 1
        db.commit()

        watchlist_imported = 0
        watchlist_skipped = 0
        for row in watchlist_rows:
            title = row.get("name", "").strip()
            if not title:
                continue
            movie = movie_cache.get((title.lower(), _parse_year(row.get("year"))))
            if movie is None:
                continue

            existing = db.scalar(
                select(WatchlistItem).where(
                    WatchlistItem.user_email == user_email, WatchlistItem.movie_id == movie.id
                )
            )
            if existing is not None:
                watchlist_skipped += 1
                continue

            db.add(WatchlistItem(user_email=user_email, movie_id=movie.id))
            watchlist_imported += 1
        db.commit()

        lists_imported = 0
        list_movies_imported = 0
        for parsed_list in parsed_lists:
            movie_list = db.scalar(
                select(MovieList).where(
                    MovieList.user_email == user_email, MovieList.name == parsed_list["name"]
                )
            )
            if movie_list is None:
                movie_list = MovieList(
                    user_email=user_email,
                    name=parsed_list["name"],
                    description=parsed_list["description"],
                )
                db.add(movie_list)
                db.flush()
            lists_imported += 1

            next_position = (
                db.scalar(
                    select(ListMovie.position)
                    .where(ListMovie.list_id == movie_list.id)
                    .order_by(ListMovie.position.desc())
                )
                or -1
            ) + 1

            for item in parsed_list["items"]:
                title, year = _item_title_year(item)
                if not title:
                    continue
                movie = movie_cache.get((title.lower(), year))
                if movie is None:
                    continue

                if db.get(ListMovie, (movie_list.id, movie.id)) is not None:
                    continue

                db.add(ListMovie(list_id=movie_list.id, movie_id=movie.id, position=next_position))
                next_position += 1
                list_movies_imported += 1
        db.commit()

        job.status = "completed"
        job.summary = {
            "diary_entries_imported": diary_imported,
            "diary_entries_skipped": diary_skipped,
            "watchlist_items_imported": watchlist_imported,
            "watchlist_items_skipped": watchlist_skipped,
            "lists_imported": lists_imported,
            "list_movies_imported": list_movies_imported,
            "unmatched_films": [
                {"title": unique_titles[key], "year": key[1]}
                for key in sorted(unmatched, key=lambda k: unique_titles[k])
            ],
        }
        db.commit()
    except Exception as error:  # noqa: BLE001 — a background job must never hang the UI on a spinner
        job = db.get(ImportJob, job_id)
        if job is not None:
            job.status = "failed"
            job.error_message = str(error)[:2000]
            db.commit()
    finally:
        db.close()


def run_import_job(job_id: int, zip_bytes: bytes) -> None:
    """Sync entry point for FastAPI's BackgroundTasks (runs in a worker thread)."""
    asyncio.run(_run_import_job_async(job_id, zip_bytes))
