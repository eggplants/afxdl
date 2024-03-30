from __future__ import annotations

import locale
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from pydantic_core import Url

from .models import Album, Track, Tracklist

if TYPE_CHECKING:
    from collections.abc import Generator

    import requests

# Change locale temporary for parsing the release date. (e.g. "August 21, 2015")
locale.setlocale(locale.LC_TIME, "en_US.UTF-8")

BASE_URL = "https://aphextwin.warp.net"


def generate_albums(session: requests.Session) -> Generator[Album, None, None]:
    for idx, _ in enumerate(iter(int, 1)):
        albums = __get_albums_by_page(idx + 1, session)
        if albums is None:
            break
        yield from albums
    return None


def __get_albums_by_page(page_idx: int, session: requests.Session) -> list[Album] | None:
    bs = BeautifulSoup(session.get(f"{BASE_URL}/fragment/index/{page_idx}").text, "html.parser")
    albums: list[Album] = []
    product_elms = bs.find_all("li", class_="product")
    if len(product_elms) < 1:
        return None
    for product_elm in product_elms:
        href = product_elm.find("a", class_="main-product-image").get("href", "")
        album_id = Path(href).name.split("-")[0]
        tracklists = tuple(__get_tracklists(album_id, session))
        if len(tracklists) < 1:
            continue
        img = product_elm.img
        date_str = product_elm.find("dd", class_="product-release-date product-release-date-past").text.strip()
        release_date = datetime.strptime(date_str, "%B %d, %Y").replace(tzinfo=timezone.utc).date()
        catalog_number_elm = product_elm.find("dd", class_="catalogue-number")
        catalog_number = catalog_number_elm.text.strip() if catalog_number_elm else None
        albums.append(
            Album(
                album_id=album_id,
                page_url=BASE_URL + href,
                title=img.get("alt", "").strip(),
                cover_url=img.get("src", ""),
                artist=product_elm.find("dd", class_="artist").find(class_="undecorated-link").text,
                release_date=release_date,
                catalog_number=catalog_number,
                tracklists=tracklists,
            ),
        )
    return albums


def __get_tracklists(album_id: str, session: requests.Session) -> list[Tracklist]:
    release_url = f"{BASE_URL}/release/{album_id}"
    # print(release_url)  # debug  # noqa: ERA001
    bs = BeautifulSoup(session.get(release_url).text, "html.parser")

    tracklists: list[Tracklist] = []
    indexed_list_elms = enumerate(bs.select("div[id^='track-list-'] > ol.track-list"))
    for list_idx, list_elm in indexed_list_elms:
        tracks: list[Track] = []
        list_number = list_idx + 1

        indexed_track_elms = enumerate(list_elm.find_all("li", class_="track player-aware"))
        for item_idx, item_elm in indexed_track_elms:
            item_number = item_idx + 1
            track_id = item_elm.get("data-id")
            resolve_url = f"{BASE_URL}/player/resolve/{album_id}-{list_number}-{item_number}"
            # print(resolve_url)  # debug  # noqa: ERA001
            page_url = Url(f"{release_url}#track-{track_id}")
            trial_url = Url(session.get(resolve_url).text.strip())

            track = Track(
                track_id=track_id,
                title=(
                    item_elm.find("h3", class_="actions-track-name") or item_elm.find("span", itemprop=True)
                ).text.strip(),
                page_url=page_url,
                trial_url=trial_url,
                number=item_number,
                duration=item_elm.find("span", class_="track-duration").text.strip(),
                description=item_elm.p.text if item_elm.p else None,
            )
            tracks.append(track)
        tracklists.append(
            Tracklist(tracks=tuple(tracks), number=list_number),
        )
    return tracklists


__all__ = ("generate_albums",)
