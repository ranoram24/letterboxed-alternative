from pydantic import BaseModel

from app.schemas.movie import MovieOut


class WhatToChooseRequest(BaseModel):
    """Client-supplied local time context — the server can't infer this reliably."""

    local_datetime: str  # local wall-clock time, e.g. "2026-08-01T22:15:00" (no UTC offset)
    timezone_offset_minutes: int | None = None  # informational; local_datetime already encodes local hour


class WhatToChooseResponse(BaseModel):
    movie: MovieOut
    reason: str
