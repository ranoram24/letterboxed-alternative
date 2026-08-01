from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.diary_entry import DiaryEntry
from app.models.list import ListMovie, MovieList
from app.models.user import User
from app.models.watchlist import WatchlistItem
from app.schemas.diary_entry import DiaryEntryCreate, DiaryEntryOut, DiaryEntryUpdate
from app.schemas.list import (
    ListMovieAdd,
    ListMovieReorder,
    MovieListCreate,
    MovieListDetailOut,
    MovieListOut,
    MovieListUpdate,
)
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemOut
from app.services.tmdb_client import get_or_cache_movie

router = APIRouter(prefix="/api/library", tags=["library"])


# ---------------------------------------------------------------------------
# Diary
# ---------------------------------------------------------------------------


@router.get("/diary", response_model=list[DiaryEntryOut])
def list_diary_entries(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    stmt = (
        select(DiaryEntry)
        .where(DiaryEntry.user_email == current_user.email)
        .order_by(DiaryEntry.watched_date.desc())
    )
    return db.scalars(stmt).all()


@router.post("/diary", response_model=DiaryEntryOut, status_code=status.HTTP_201_CREATED)
async def create_diary_entry(
    payload: DiaryEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie = await get_or_cache_movie(db, payload.tmdb_id)
    entry = DiaryEntry(
        user_email=current_user.email,
        movie_id=movie.id,
        watched_date=payload.watched_date,
        rating=payload.rating,
        rewatch=payload.rewatch,
        review_text=payload.review_text,
        tags=payload.tags,
        liked=payload.liked,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _get_owned_diary_entry(db: Session, current_user: User, entry_id: int) -> DiaryEntry:
    entry = db.get(DiaryEntry, entry_id)
    if entry is None or entry.user_email != current_user.email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diary entry not found")
    return entry


@router.get("/diary/{entry_id}", response_model=DiaryEntryOut)
def get_diary_entry(
    entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _get_owned_diary_entry(db, current_user, entry_id)


@router.patch("/diary/{entry_id}", response_model=DiaryEntryOut)
def update_diary_entry(
    entry_id: int,
    payload: DiaryEntryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = _get_owned_diary_entry(db, current_user, entry_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/diary/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diary_entry(
    entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    entry = _get_owned_diary_entry(db, current_user, entry_id)
    db.delete(entry)
    db.commit()


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------


@router.get("/watchlist", response_model=list[WatchlistItemOut])
def list_watchlist(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = (
        select(WatchlistItem)
        .where(WatchlistItem.user_email == current_user.email)
        .order_by(WatchlistItem.added_date.desc())
    )
    return db.scalars(stmt).all()


@router.post("/watchlist", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    payload: WatchlistItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie = await get_or_cache_movie(db, payload.tmdb_id)

    existing = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_email == current_user.email, WatchlistItem.movie_id == movie.id
        )
    )
    if existing is not None:
        return existing

    item = WatchlistItem(user_email=current_user.email, movie_id=movie.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/watchlist/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    movie_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    item = db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_email == current_user.email, WatchlistItem.movie_id == movie_id
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not on watchlist")
    db.delete(item)
    db.commit()


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------


def _get_owned_list(db: Session, current_user: User, list_id: int) -> MovieList:
    movie_list = db.get(MovieList, list_id)
    if movie_list is None or movie_list.user_email != current_user.email:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    return movie_list


@router.get("/lists", response_model=list[MovieListOut])
def list_lists(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stmt = (
        select(MovieList)
        .where(MovieList.user_email == current_user.email)
        .order_by(MovieList.created_at.desc())
    )
    return db.scalars(stmt).all()


@router.post("/lists", response_model=MovieListOut, status_code=status.HTTP_201_CREATED)
def create_list(
    payload: MovieListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie_list = MovieList(
        user_email=current_user.email, name=payload.name, description=payload.description
    )
    db.add(movie_list)
    db.commit()
    db.refresh(movie_list)
    return movie_list


@router.get("/lists/{list_id}", response_model=MovieListDetailOut)
def get_list(
    list_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _get_owned_list(db, current_user, list_id)


@router.patch("/lists/{list_id}", response_model=MovieListOut)
def update_list(
    list_id: int,
    payload: MovieListUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie_list = _get_owned_list(db, current_user, list_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(movie_list, field, value)
    db.commit()
    db.refresh(movie_list)
    return movie_list


@router.delete("/lists/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_list(
    list_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    movie_list = _get_owned_list(db, current_user, list_id)
    db.delete(movie_list)
    db.commit()


@router.post(
    "/lists/{list_id}/movies", response_model=MovieListDetailOut, status_code=status.HTTP_201_CREATED
)
async def add_movie_to_list(
    list_id: int,
    payload: ListMovieAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie_list = _get_owned_list(db, current_user, list_id)
    movie = await get_or_cache_movie(db, payload.tmdb_id)

    existing = db.get(ListMovie, (list_id, movie.id))
    if existing is None:
        next_position = (
            db.scalar(select(ListMovie.position).where(ListMovie.list_id == list_id).order_by(
                ListMovie.position.desc()
            ))
            or -1
        ) + 1
        db.add(ListMovie(list_id=list_id, movie_id=movie.id, position=next_position))
        db.commit()

    db.refresh(movie_list)
    return movie_list


@router.patch("/lists/{list_id}/movies/reorder", response_model=MovieListDetailOut)
def reorder_list_movies(
    list_id: int,
    payload: ListMovieReorder,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    movie_list = _get_owned_list(db, current_user, list_id)

    items_by_movie_id = {item.movie_id: item for item in movie_list.items}
    if set(payload.movie_ids) != set(items_by_movie_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="movie_ids must contain exactly the movies currently in the list",
        )

    for position, movie_id in enumerate(payload.movie_ids):
        items_by_movie_id[movie_id].position = position

    db.commit()
    db.refresh(movie_list)
    return movie_list


@router.delete("/lists/{list_id}/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_movie_from_list(
    list_id: int,
    movie_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_list(db, current_user, list_id)
    item = db.get(ListMovie, (list_id, movie_id))
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not in list")
    db.delete(item)
    db.commit()
