"""Download tracks by using album data."""

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING, NamedTuple
from unicodedata import normalize

# mutagen is marked as pyted package, but almost interfaces are untyped.
from mutagen._file import (
    File as MutagenFile,  # pyright: ignore[reportUnknownVariableType]
)
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC, COMM
from mutagen.id3._util import error as MutagenUtilError  # noqa: N812
from mutagen.mp3 import EasyMP3

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from requests import Session

    from .models import Album, Track, Tracklist


class Metadata(NamedTuple):
    """Metadata for a track."""

    album: Album
    tracklist: Tracklist
    track: Track
    total_disk: int
    total_track: int


def download(
    album: Album,
    session: Session,
    *,
    save_dir: Path,
    overwrite: bool = False,
    dry: bool = False,
) -> Path | None:
    """Download tracks by using album data.

    Args:
        album (Album): Album data to download.
        session (Session): Session object for downloading.
        save_dir (Path): Directory to save albums.
        overwrite (bool): Overwrite saved albums. Defaults to False.
        dry(bool): Dry run mode (skip downloading and saving). Defaults to False.

    Returns:
        Path | None: Path to saved album directory or None if album is already saved.
    """
    album_dir = save_dir / __slugify(f"{album.album_id}-{album.title}")
    if album_dir.exists() and not overwrite:
        return None

    if dry:
        return album_dir

    album_dir.mkdir(parents=True, exist_ok=True)
    for metadata in __generate_track_metadata(album):
        __save_track(album_dir, session, metadata)
    return album_dir


def __generate_track_metadata(
    album: Album,
) -> Generator[Metadata, None, None]:
    """Generate metadata for each track.

    Args:
        album (Album):  Album data.

    Yields:
        Generator[Metadata, None, None]: Metadata for each track.
    """
    total_disk = len(album.tracklists)
    for tracklist in album.tracklists:
        total_track = len(tracklist.tracks)

        for track in tracklist.tracks:
            yield Metadata(
                album=album,
                tracklist=tracklist,
                track=track,
                total_disk=total_disk,
                total_track=total_track,
            )


def __save_track(
    album_dir: Path,
    session: Session,
    metadata: Metadata,
) -> None:
    """Save track data to a file.

    Args:
        album_dir (Path): Directory to save tracks.
        session (Session): Session object for downloading.
        metadata (Metadata): Metadata for a track.
    """
    (
        album,
        tracklist,
        track,
        total_disk,
        total_track,
    ) = metadata

    res = session.get(str(track.trial_url))
    if not res.ok or res.headers.get("Content-Type") != "audio/mpeg":
        raise ValueError

    audio_path = album_dir / (__slugify(f"{track.track_id}-{track.title}") + ".mp3")
    with audio_path.open("wb") as f:
        f.write(res.content)

    audio = MutagenFile(audio_path, easy=True)

    if not isinstance(audio, EasyID3 | EasyMP3):
        msg = f"Failed to load audio file: {audio_path}"
        raise TypeError(msg)
    if type(audio) is EasyMP3:
        with contextlib.suppress(MutagenUtilError):
            audio.add_tags()  # type: ignore[no-untyped-call]

    audio["title"] = track.title
    audio["artist"] = album.artist
    audio["album"] = album.title
    audio["albumartist"] = album.artist
    audio["genre"] = "Electronic"
    audio["tracknumber"] = f"{track.number}/{total_track}"
    audio["discnumber"] = f"{tracklist.number}/{total_disk}"
    if album.catalog_number:
        audio["catalognumber"] = album.catalog_number
    audio["website"] = str(album.page_url)

    release_date = album.release_date.isoformat()
    audio["date"] = release_date
    audio["originaldate"] = release_date
    audio.save()  # pyright: ignore[reportUnknownMemberType]

    audio = ID3(audio_path)  # type: ignore[no-untyped-call]
    res = session.get(str(album.cover_url))
    audio.add(  # pyright: ignore[reportUnknownMemberType]
        APIC(  # type: ignore[no-untyped-call]
            mime=res.headers["Content-Type"],
            type=3,
            data=res.content,
        ),
    )
    if track.description:
        audio.add(  # pyright: ignore[reportUnknownMemberType]
            COMM(  # type: ignore[no-untyped-call]
                encoding=3,
                lang="eng",
                desc="Description",
                text=[track.description],
            ),
        )
    audio.save()  # pyright: ignore[reportUnknownMemberType]


def __slugify(target: str) -> str:
    """Slugify a string.

    Args:
        target (str): String to slugify.

    Returns:
        str: Slugified string.
    """
    slug = re.sub(r"[^\w\s-]", "", normalize("NFKC", target).lower())
    return re.sub(r"[-\s]+", "-", slug).strip("-_")


__all__ = ("download",)
