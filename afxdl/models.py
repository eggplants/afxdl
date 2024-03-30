from __future__ import annotations

from datetime import date  # noqa: TCH003

from pydantic import BaseModel, Field, HttpUrl


class StrictBaseModel(BaseModel):
    class Config:
        validate_assignment = True


class Track(StrictBaseModel):
    track_id: str = Field(..., min_length=6, max_length=7, pattern=r"^\d{6,7}$")
    title: str = Field(..., min_length=1)
    page_url: HttpUrl
    number: int = Field(..., gt=0)
    duration: str = Field(..., min_length=4, pattern=r"^\d{1,2}:\d{2}$")
    description: str | None = Field(..., min_length=1)
    trial_url: HttpUrl


class Tracklist(StrictBaseModel):
    tracks: tuple[Track, ...] = Field(..., min_length=1)
    number: int = Field(..., gt=0)


class Album(StrictBaseModel):
    album_id: str = Field(..., min_length=5, max_length=6, pattern=r"^\d{5,6}$")
    title: str = Field(..., min_length=1)
    artist: str = Field(..., min_length=1)
    cover_url: HttpUrl
    page_url: HttpUrl
    tracklists: tuple[Tracklist, ...] = Field(..., min_length=1)
    release_date: date
    catalog_number: str | None = Field(..., min_length=1)


__all__ = (
    "Album",
    "Tracklist",
    "Track",
)
