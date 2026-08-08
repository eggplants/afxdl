"""Parser module for the Aphex Twin's discography from the website."""

from __future__ import annotations

import contextlib
import locale
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from pydantic import HttpUrl
from wafsolver import (
    ACTION_HEADER,
    TOKEN_COOKIE,
    WafSolveError,
    is_challenged,
    solve_challenge,
)

from .models import Album, Track, Tracklist
from .progress import noop_progress

if TYPE_CHECKING:
    from collections.abc import Generator

    from requests import Response, Session

    from .progress import ProgressCallback

# Change locale temporary for parsing the release date. (e.g. "August 21, 2015")
try:
    locale.setlocale(locale.LC_TIME, "en_US.UTF-8")
except locale.Error:
    # Fallback to C.UTF-8 or system default if en_US.UTF-8 is not available
    with contextlib.suppress(locale.Error):
        locale.setlocale(locale.LC_TIME, "C.UTF-8")

# Base URL for the website.
BASE_URL = "https://aphextwin.warp.net"


class FetchError(Exception):
    """Raised when the website does not return the expected content."""


class _AlbumStub(NamedTuple):
    """Album data taken from the release list, before its tracklists are known."""

    album_id: str
    page_url: str
    title: str
    cover_url: str
    artist: str
    release_date: date
    catalog_number: str | None


def __fetch(url: str, session: Session) -> Response:
    """Fetch a URL and make sure the response is really from the website.

    The site sits behind AWS WAF, which answers bot-like requests with a
    JavaScript challenge page instead of the content. When that happens the
    challenge is solved once and the resulting token is kept on the session,
    so later requests go straight through.

    Args:
        url (str): The URL to fetch.
        session (Session): A requests session.

    Raises:
        FetchError: If the response is a WAF challenge that could not be
            solved, or an error status.

    Returns:
        Response: The response.
    """
    res = session.get(url)
    if is_challenged(res.headers):
        res = __solve_challenge(url, session, res.text)

    waf_action = res.headers.get(ACTION_HEADER)
    if waf_action:
        msg = (
            f"{url} was blocked by AWS WAF (x-amzn-waf-action: {waf_action}) "
            "and the challenge could not be solved."
        )
        raise FetchError(msg)
    if not res.ok:
        msg = f"{url} returned HTTP {res.status_code}."
        raise FetchError(msg)
    return res


def __solve_challenge(url: str, session: Session, challenge_html: str) -> Response:
    """Solve a WAF challenge, store the token, and retry the request once.

    Args:
        url (str): The URL that was challenged.
        session (Session): A requests session; the token is stored on it.
        challenge_html (str): The challenge page body.

    Raises:
        FetchError: If the challenge could not be solved.

    Returns:
        Response: The response to the retried request.
    """
    domain = urlparse(BASE_URL).hostname or ""
    try:
        token = solve_challenge(domain, challenge_html)
    except WafSolveError as err:
        raise FetchError(str(err)) from err
    session.cookies.set(TOKEN_COOKIE, token, domain=domain)
    return session.get(url)


def generate_albums(
    session: Session,
    *,
    progress: ProgressCallback = noop_progress,
) -> Generator[Album, None, None]:
    """Fetch albums from the website.

    The release list only carries the album metadata, so each album needs one
    more request for its tracklists. That request is made right before the
    album is yielded rather than for the whole page at once, so the caller can
    start downloading the first album without waiting for the last one.

    Args:
        session (Session): A requests session.
        progress (ProgressCallback): Called with a status line before each
            request. Defaults to discarding the messages.

    Yields:
        Album: An album object.

    Returns:
        None: When there are no more albums to fetch.
    """
    for idx, _ in enumerate(iter(int, 1)):
        page_idx = idx + 1
        progress(f"Fetching release list (page {page_idx})...")
        stubs = __get_album_stubs_by_page(page_idx, session)
        if stubs is None:
            progress("No more releases.")
            break
        progress(f"Found {len(stubs)} release(s) on page {page_idx}.")
        for stub_idx, stub in enumerate(stubs, start=1):
            progress(
                f"Fetching tracklist of {stub.title!r} "
                f"({stub_idx}/{len(stubs)} on page {page_idx})...",
            )
            tracklists = tuple(__get_tracklists(stub.album_id, session))
            if len(tracklists) < 1:
                progress(f"{stub.title!r} has no tracklist, skipping.")
                continue
            yield Album(
                album_id=stub.album_id,
                page_url=HttpUrl(BASE_URL + stub.page_url),
                title=stub.title,
                cover_url=HttpUrl(stub.cover_url),
                artist=stub.artist,
                release_date=stub.release_date,
                catalog_number=stub.catalog_number,
                tracklists=tracklists,
            )
    return None


def __get_album_stubs_by_page(
    page_idx: int,
    session: Session,
) -> list[_AlbumStub] | None:
    """Fetch the album metadata listed on a specific page.

    Args:
        page_idx (int): The page index.
        session (Session): A requests session.

    Returns:
        list[_AlbumStub] | None: The albums on the page, or None if the page is
            empty and there is nothing left to fetch.
    """
    bs = BeautifulSoup(
        __fetch(f"{BASE_URL}/fragment/releases/{page_idx}", session).text,
        "html.parser",
    )
    stubs: list[_AlbumStub] = []
    product_elms = bs.find_all("li", class_="product")
    if len(product_elms) < 1:
        return None
    for product_elm in product_elms:
        a_tag = product_elm.find("a", class_="main-product-image")
        assert a_tag is not None
        href = str(a_tag.get("href", ""))
        album_id = Path(href).name.split("-")[0]
        img = product_elm.img
        if img is None:
            continue
        # The element also carries a -past/-future modifier class; matching only
        # the base class keeps unreleased (pre-order) titles working too.
        date_tag = product_elm.find("dd", class_="product-release-date")
        assert date_tag is not None
        date_str = date_tag.text.strip()
        release_date = (
            datetime.strptime(date_str, "%B %d, %Y").replace(tzinfo=UTC).date()
        )
        catalog_number_elm = product_elm.find("dd", class_="catalogue-number")
        artist_dd = product_elm.find("dd", class_="artist")
        assert artist_dd is not None
        artist_tag = artist_dd.find(class_="undecorated-link")
        assert artist_tag is not None
        stubs.append(
            _AlbumStub(
                album_id=album_id,
                page_url=href,
                title=str(img.get("alt", "")).strip(),
                cover_url=str(img.get("src", "")),
                artist=artist_tag.text,
                release_date=release_date,
                catalog_number=(
                    catalog_number_elm.text.strip() if catalog_number_elm else None
                ),
            ),
        )
    return stubs


def __get_tracklists(album_id: str, session: Session) -> list[Tracklist]:
    """Fetch tracklists from an album.

    Args:
        album_id (str): The album ID.
        session (Session): A requests session.

    Returns:
        list[Tracklist]: A list of tracklists. The tracks carry no ``trial_url``
            yet; see `resolve_trial_url`.
    """
    release_url = f"{BASE_URL}/release/{album_id}"
    # print(release_url)  # debug  # noqa: ERA001
    bs = BeautifulSoup(__fetch(release_url, session).text, "html.parser")

    tracklists: list[Tracklist] = []
    indexed_list_elms = enumerate(bs.select("div[id^='track-list-'] > ol.track-list"))
    for list_idx, list_elm in indexed_list_elms:
        tracks: list[Track] = []
        list_number = list_idx + 1

        for item_idx, item_elm in enumerate(
            list_elm.find_all("li", class_="track player-aware"),
        ):
            item_number = item_idx + 1
            track_id = item_elm.get("data-id")
            title_tag = item_elm.find(
                "h3", class_="actions-track-name"
            ) or item_elm.find("span", itemprop=True)
            assert title_tag is not None
            duration_tag = item_elm.find("span", class_="track-duration")
            assert duration_tag is not None
            tracks.append(
                Track(
                    track_id=str(track_id),
                    title=title_tag.text.strip(),
                    page_url=HttpUrl(f"{release_url}#track-{track_id}"),
                    number=item_number,
                    duration=duration_tag.text.strip(),
                    description=item_elm.p.text if item_elm.p else None,
                ),
            )
        tracklists.append(
            Tracklist(tracks=tuple(tracks), number=list_number),
        )
    return tracklists


def resolve_trial_url(
    album_id: str,
    tracklist_number: int,
    track_number: int,
    session: Session,
) -> HttpUrl:
    """Ask the site for the audio URL of a single track.

    This costs one request per track, so it is done only for tracks that are
    about to be downloaded instead of for every track of every listed album.

    Args:
        album_id (str): The album ID.
        tracklist_number (int): The 1-based tracklist (disc) number.
        track_number (int): The 1-based track number within the tracklist.
        session (Session): A requests session.

    Returns:
        HttpUrl: The URL of the audio file.
    """
    resolve_url = (
        f"{BASE_URL}/player/resolve/{album_id}-{tracklist_number}-{track_number}"
    )
    return HttpUrl(__fetch(resolve_url, session).text.strip())


__all__ = ("FetchError", "generate_albums", "resolve_trial_url")
