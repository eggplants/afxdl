from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import pytest
from pydantic import HttpUrl
from wafsolver import TOKEN_COOKIE, WafSolveError

from afxdl import __version__
from afxdl.main import main
from afxdl.models import Album, Track, Tracklist
from afxdl.parse import BASE_URL, FetchError, generate_albums, resolve_trial_url

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


def test_main_reports_fetch_error(
    capfd: pytest.CaptureFixture[str],
    temp_dir: Path,
) -> None:
    """Test main function exits with an error when the site blocks the request."""

    def blocked() -> Generator[Album, None, None]:
        msg = "blocked"
        raise FetchError(msg)
        yield

    with patch("afxdl.main.generate_albums") as mock_gen:
        mock_gen.return_value = blocked()

        with pytest.raises(SystemExit) as e:
            main(test_args=[str(temp_dir)])

        assert e.value.code == 1
        captured = capfd.readouterr()
        assert "[!] blocked" in captured.err
        assert "[+] All Finished!" not in captured.out


def test_generate_albums_solves_waf_challenge() -> None:
    """Test that a WAF challenge is solved and the request retried."""
    challenge = Mock(
        headers={"x-amzn-waf-action": "challenge"},
        ok=True,
        status_code=202,
        text="<challenge page>",
    )
    empty_page = Mock(headers={}, ok=True, status_code=200, text="<html></html>")
    session = Mock()
    session.get.side_effect = [challenge, empty_page]

    with patch("afxdl.parse.solve_challenge", return_value="tok") as mock_solve:
        assert list(generate_albums(session)) == []

    mock_solve.assert_called_once_with("aphextwin.warp.net", "<challenge page>")
    session.cookies.set.assert_called_once_with(
        TOKEN_COOKIE,
        "tok",
        domain="aphextwin.warp.net",
    )


def test_generate_albums_reports_unsolvable_challenge() -> None:
    """Test that a challenge which cannot be solved is reported."""
    session = Mock()
    session.get.return_value = Mock(
        headers={"x-amzn-waf-action": "challenge"},
        ok=True,
        status_code=202,
        text="<challenge page>",
    )

    with (
        patch("afxdl.parse.solve_challenge", side_effect=WafSolveError("nope")),
        pytest.raises(FetchError, match="nope"),
    ):
        next(generate_albums(session))


RELEASE_LIST_HTML = """
<ul>
  <li class="product">
    <a class="main-product-image" href="/release/12345-test-album"></a>
    <img alt="Test Album" src="https://example.com/cover.jpg">
    <dd class="product-release-date">August 21, 2015</dd>
    <dd class="catalogue-number">TEST001</dd>
    <dd class="artist"><span class="undecorated-link">Aphex Twin</span></dd>
  </li>
  <li class="product">
    <a class="main-product-image" href="/release/67890-test-album-2"></a>
    <img alt="Test Album 2" src="https://example.com/cover2.jpg">
    <dd class="product-release-date">August 22, 2015</dd>
    <dd class="catalogue-number">TEST002</dd>
    <dd class="artist"><span class="undecorated-link">Aphex Twin</span></dd>
  </li>
</ul>
"""

RELEASE_HTML = """
<div id="track-list-1">
  <ol class="track-list">
    <li class="track player-aware" data-id="123456">
      <h3 class="actions-track-name">Track One</h3>
      <span class="track-duration">3:45</span>
    </li>
  </ol>
</div>
"""


def _recording_session(urls: list[str]) -> Mock:
    """Build a session mock that serves the fixtures above and records URLs."""

    def get(url: str) -> Mock:
        urls.append(url)
        if url == f"{BASE_URL}/fragment/releases/1":
            text = RELEASE_LIST_HTML
        elif url.startswith(f"{BASE_URL}/release/"):
            text = RELEASE_HTML
        else:
            text = "<html></html>"
        return Mock(headers={}, ok=True, status_code=200, text=text)

    session = Mock()
    session.get.side_effect = get
    return session


def test_generate_albums_fetches_tracklists_lazily() -> None:
    """Test that only the yielded album's tracklist is fetched."""
    urls: list[str] = []
    messages: list[str] = []
    generator = generate_albums(_recording_session(urls), progress=messages.append)

    album = next(generator)

    assert album.title == "Test Album"
    assert album.album_id == "12345"
    # The second album's release page is untouched, and no /player/resolve/
    # request is made while parsing.
    assert urls == [
        f"{BASE_URL}/fragment/releases/1",
        f"{BASE_URL}/release/12345",
    ]
    assert album.tracklists[0].tracks[0].trial_url is None
    assert any("Fetching release list" in message for message in messages)
    assert any("Test Album" in message for message in messages)

    assert next(generator).title == "Test Album 2"
    assert urls[-1] == f"{BASE_URL}/release/67890"


def test_resolve_trial_url() -> None:
    """Test that the audio URL is resolved from the disc and track numbers."""
    session = Mock()
    session.get.return_value = Mock(
        headers={},
        ok=True,
        status_code=200,
        text="https://example.com/audio.mp3\n",
    )

    url = resolve_trial_url("12345", 2, 3, session)

    assert str(url) == "https://example.com/audio.mp3"
    session.get.assert_called_once_with(f"{BASE_URL}/player/resolve/12345-2-3")


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
