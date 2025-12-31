from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from pydantic import HttpUrl

from afxdl import __version__
from afxdl.main import main
from afxdl.models import Album, Track, Tracklist

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def sample_track() -> Track:
    """Create a sample track for testing."""
    return Track(
        track_id="123456",
        title="Test Track",
        page_url=HttpUrl("https://example.com/track"),
        number=1,
        duration="3:45",
        description="Test Description",
        trial_url=HttpUrl("https://example.com/audio.mp3"),
    )


@pytest.fixture
def sample_tracklist(sample_track: Track) -> Tracklist:
    """Create a sample tracklist for testing."""
    return Tracklist(
        tracks=(sample_track,),
        number=1,
    )


@pytest.fixture
def sample_album(sample_tracklist: Tracklist) -> Album:
    """Create a sample album for testing."""
    return Album(
        album_id="12345",
        title="Test Album",
        artist="Test Artist",
        cover_url=HttpUrl("https://example.com/cover.jpg"),
        page_url=HttpUrl("https://example.com/album"),
        tracklists=(sample_tracklist,),
        release_date=date(2020, 1, 1),
        catalog_number="TEST001",
    )


@pytest.fixture
def temp_dir() -> Generator[Path, Any, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_version() -> None:
    """Test version string."""
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_cli_help(capfd: pytest.CaptureFixture[str]) -> None:
    """Test CLI help output."""
    with pytest.raises(SystemExit) as e:
        main(test_args=["-h"])
    assert e.value.code == 0
    captured = capfd.readouterr()
    assert "usage:" in captured.out
    assert "afxdl" in captured.out
    assert "download audio" in captured.out
    assert not captured.err


def test_cli_version(capfd: pytest.CaptureFixture[str]) -> None:
    """Test CLI version output."""
    with pytest.raises(SystemExit) as e:
        main(test_args=["-V"])
    assert e.value.code == 0
    captured = capfd.readouterr()
    assert __version__ in captured.out
    assert not captured.err


def test_main_with_default_dir(
    capfd: pytest.CaptureFixture[str],
    temp_dir: Path,
    sample_album: Album,
) -> None:
    """Test main function with default directory."""
    with (
        patch("afxdl.main.generate_albums") as mock_gen,
        patch("afxdl.main.download") as mock_download,
    ):
        mock_gen.return_value = iter([sample_album, True])
        mock_download.return_value = temp_dir / "test-album"

        main(test_args=[str(temp_dir)])

        captured = capfd.readouterr()
        assert "[+] Found:" in captured.out
        assert "Test Album" in captured.out
        assert "[+] Saved:" in captured.out
        assert "[+] All Finished!" in captured.out


def test_main_with_overwrite(
    capfd: pytest.CaptureFixture[str],
    temp_dir: Path,
    sample_album: Album,
) -> None:
    """Test main function with overwrite option."""
    with (
        patch("afxdl.main.generate_albums") as mock_gen,
        patch("afxdl.main.download") as mock_download,
    ):
        mock_gen.return_value = iter([sample_album, True])
        mock_download.return_value = temp_dir / "test-album"

        main(test_args=[str(temp_dir), "-o"])

        captured = capfd.readouterr()
        assert "[+] Found:" in captured.out
        assert "Test Album" in captured.out


def test_main_with_dry_run(
    capfd: pytest.CaptureFixture[str],
    temp_dir: Path,
    sample_album: Album,
) -> None:
    """Test main function with dry run option."""
    with (
        patch("afxdl.main.generate_albums") as mock_gen,
        patch("afxdl.main.download") as mock_download,
    ):
        mock_gen.return_value = iter([sample_album, True])
        mock_download.return_value = temp_dir / "test-album"

        main(test_args=[str(temp_dir), "-d"])

        captured = capfd.readouterr()
        assert "[+] Found:" in captured.out
        assert "Test Album" in captured.out
        assert "[!] Skipped in dry run mode." in captured.out
        assert "[+] All Finished!" in captured.out


def test_main_skip_existing_album(
    capfd: pytest.CaptureFixture[str],
    temp_dir: Path,
    sample_album: Album,
) -> None:
    """Test main function skipping existing album."""
    with (
        patch("afxdl.main.generate_albums") as mock_gen,
        patch("afxdl.main.download") as mock_download,
    ):
        mock_gen.return_value = iter([sample_album, True])
        mock_download.return_value = None  # Indicates album already exists

        main(test_args=[str(temp_dir)])

        captured = capfd.readouterr()
        assert "[+] Found:" in captured.out
        assert "[!] Skipped since album already exists." in captured.out
        assert "[+] All Finished!" in captured.out


def test_main_with_multiple_albums(
    capfd: pytest.CaptureFixture[str],
    temp_dir: Path,
    sample_album: Album,
) -> None:
    """Test main function with multiple albums."""
    album2 = Album(
        album_id="67890",
        title="Test Album 2",
        artist="Test Artist",
        cover_url=HttpUrl("https://example.com/cover2.jpg"),
        page_url=HttpUrl("https://example.com/album2"),
        tracklists=sample_album.tracklists,
        release_date=date(2021, 1, 1),
        catalog_number="TEST002",
    )

    with (
        patch("afxdl.main.generate_albums") as mock_gen,
        patch("afxdl.main.download") as mock_download,
    ):
        mock_gen.return_value = iter([sample_album, album2, True])
        mock_download.side_effect = [
            temp_dir / "test-album",
            temp_dir / "test-album-2",
        ]

        main(test_args=[str(temp_dir)])

        captured = capfd.readouterr()
        assert captured.out.count("[+] Found:") == 2  # noqa: PLR2004
        assert "Test Album" in captured.out
        assert "Test Album 2" in captured.out


def test_main_empty_album_generator(
    capfd: pytest.CaptureFixture[str],
    temp_dir: Path,
) -> None:
    """Test main function with empty album generator."""
    with patch("afxdl.main.generate_albums") as mock_gen:
        mock_gen.return_value = iter([True])

        main(test_args=[str(temp_dir)])

        captured = capfd.readouterr()
        assert "[+] All Finished!" in captured.out


def test_track_model_validation(sample_track: Track) -> None:
    """Test track model validation."""
    assert sample_track.track_id == "123456"
    assert sample_track.title == "Test Track"
    assert sample_track.number == 1


def test_track_model_invalid_id() -> None:
    """Test track model with invalid track_id."""
    with pytest.raises(ValueError, match="track_id"):
        Track(
            track_id="123",  # Too short
            title="Test Track",
            page_url=HttpUrl("https://example.com/track"),
            number=1,
            duration="3:45",
            description="Test",
            trial_url=HttpUrl("https://example.com/audio.mp3"),
        )


def test_tracklist_model_validation(sample_tracklist: Tracklist) -> None:
    """Test tracklist model validation."""
    assert len(sample_tracklist.tracks) == 1
    assert sample_tracklist.number == 1


def test_album_model_validation(sample_album: Album) -> None:
    """Test album model validation."""
    assert sample_album.album_id == "12345"
    assert sample_album.title == "Test Album"
    assert sample_album.artist == "Test Artist"
    assert len(sample_album.tracklists) == 1


def test_album_model_invalid_id() -> None:
    """Test album model with invalid album_id."""
    with pytest.raises(ValueError, match="album_id"):
        Album(
            album_id="123",  # Too short
            title="Test Album",
            artist="Test Artist",
            cover_url=HttpUrl("https://example.com/cover.jpg"),
            page_url=HttpUrl("https://example.com/album"),
            tracklists=(),
            release_date=date(2020, 1, 1),
            catalog_number="TEST001",
        )
