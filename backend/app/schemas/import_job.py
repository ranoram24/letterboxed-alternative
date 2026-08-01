from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UnmatchedFilm(BaseModel):
    title: str
    year: int | None


class ImportSummary(BaseModel):
    diary_entries_imported: int
    diary_entries_skipped: int
    watchlist_items_imported: int
    watchlist_items_skipped: int
    lists_imported: int
    list_movies_imported: int
    unmatched_films: list[UnmatchedFilm]


class ImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    total_films: int | None
    processed_films: int
    summary: ImportSummary | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
