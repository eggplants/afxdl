from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING, NamedTuple
from unicodedata import normalize

# mutagen is marked as pyted package, but almost interfaces are untyped.
from mutagen._file import File as MutagenFile
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC
from mutagen.id3._util import error as MutagenUtilError  # noqa: N812
from mutagen.mp3 import EasyMP3

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from requests import Session

    from .models import Album, Track, Tracklist


class Metadata(NamedTuple):
    album: Album
    tracklist: Tracklist
    track: Track
    total_disk: int
    total_track: int


def download(album: Album, session: Session, *, save_dir: Path, overwrite: bool = False) -> bool:
    album_dir = save_dir / __slugify(f"{album.album_id}-{album.title}")
    if album_dir.exists() and not overwrite:
        return False

    album_dir.mkdir(parents=True, exist_ok=True)
    for metadata in __generate_track_metadata(album):
        __save_track(album_dir, session, metadata)
    return True


def __generate_track_metadata(
    album: Album,
) -> Generator[Metadata, None, None]:
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
    (
        album,
        tracklist,
        track,
        total_disk,
        total_track,
    ) = metadata

    res = session.get(str(track.trial_url))
    if not res.ok or res.headers.get("Content-Type") != "audio/mpeg":
        # breakpoint()  # debug  # noqa: ERA001
        return
    audio_path = album_dir / (__slugify(f"{track.track_id}-{track.title}") + ".mp3")
    with audio_path.open("wb") as f:
        f.write(res.content)
    audio = MutagenFile(audio_path, easy=True)
    with contextlib.suppress(MutagenUtilError):
        audio.add_tags()
    if not isinstance(audio, (EasyID3, EasyMP3)):
        # breakpoint()  # debug  # noqa: ERA001
        return
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
    audio.save()

    audio = ID3(audio_path)  # type: ignore[no-untyped-call]
    res = session.get(str(album.cover_url))
    image_type = "audio/mpeg"
    audio.add(  # type: ignore[no-untyped-call]
        APIC(  # type: ignore[no-untyped-call]
            mime=image_type,
            type=3,
            data=res.content,
        ),
    )
    audio.save()


def __slugify(target: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", normalize("NFKC", target).lower())
    return re.sub(r"[-\s]+", "-", slug).strip("-_")


__all__ = ("download",)
