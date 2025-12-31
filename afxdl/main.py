"""Main module for afxdl."""

from __future__ import annotations

import argparse
from pathlib import Path
from shutil import get_terminal_size

import requests
from requests.adapters import HTTPAdapter, Retry

from . import __version__
from .download import download
from .parse import generate_albums


class CustomFormatter(
    argparse.ArgumentDefaultsHelpFormatter,
    argparse.RawDescriptionHelpFormatter,
):
    """Custom formatter for argparse."""


def __dir_path(path_str: str) -> Path:
    """Validate path string.

    Args:
        path_str (str): Path string.

    Raises:
        argparse.ArgumentTypeError: If path is not a valid path.

    Returns:
        Path: Path object.
    """
    path = Path(path_str)
    if not path.exists() or path.is_dir():
        return path

    msg = f"{path} is not a valid path for save dir."
    raise argparse.ArgumentTypeError(msg)


def __parse_args(test_args: list[str] | None = None) -> argparse.Namespace:
    """Parse arguments.

    Args:
        test_args (list[str] | None, optional): Test arguments. Defaults to None.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="afxdl",
        description="download audio from <aphextwin.warp.net>",
        formatter_class=(
            lambda prog: CustomFormatter(
                prog,
                width=get_terminal_size(fallback=(120, 50)).columns,
            )
        ),
    )
    parser.add_argument(
        "save_dir",
        nargs="?",
        type=__dir_path,
        default="./AphexTwin/",
        help="directory to save albums (default: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="overwrite saved albums",
    )
    parser.add_argument(
        "-d",
        "--dry",
        action="store_true",
        help="dry run mode (skip downloading and saving)",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=__version__,
    )
    if test_args is None:
        return parser.parse_args()
    return parser.parse_args(test_args)


def main(test_args: list[str] | None = None) -> None:
    """Main function for afxdl.

    Args:
        test_args (list[str] | None, optional): Test arguments. Defaults to None.
    """
    args = __parse_args(test_args)
    with requests.Session() as session:
        session.headers["User-Agent"] = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
        session.mount(
            "https://",
            HTTPAdapter(
                max_retries=Retry(
                    total=5,
                    backoff_factor=10,
                    status_forcelist=[429, 500, 502, 503, 504],
                ),
            ),
        )

        album_generator = generate_albums(session)
        for idx, _ in enumerate(iter(int, 1)):
            print(f"[λ] === {idx + 1:03} ===")
            print("[-] Fetching album information...")
            album = next(album_generator, True)
            if isinstance(album, bool):
                break
            total_track = sum(len(tl.tracks) for tl in album.tracklists)
            print(f"[+] Found: {album.title!r} ({total_track} tracks)")
            print("[-] Downloading albums...")
            album_dir = download(
                album,
                session,
                save_dir=args.save_dir,
                overwrite=bool(args.overwrite),
                dry=bool(args.dry),
            )
            if args.dry:
                print("[!] Skipped in dry run mode.")
            elif album_dir:
                print(f"[+] Saved: {str(album_dir)!r}")
            else:
                print("[!] Skipped since album already exists. (use `-o` to overwrite)")
    return print("[+] All Finished!")


if __name__ == "__main__":
    main()

__all__ = ("main",)
