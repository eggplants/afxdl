from __future__ import annotations

import argparse
from os import get_terminal_size
from pathlib import Path

import requests

from . import __version__
from .download import download
from .parse import generate_albums


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


def __dir_path(path_str: str) -> Path:
    path = Path(path_str)
    if not path.exists() or path.is_dir():
        return path

    msg = f"{path} is not a valid path for save dir."
    raise argparse.ArgumentTypeError(msg)


def __parse_args(test_args: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="afxdl",
        description="download audio from <aphextwin.warp.net>",
        formatter_class=(
            lambda prog: CustomFormatter(
                prog,
                width=get_terminal_size().columns,
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
        "-V",
        "--version",
        action="version",
        version=__version__,
    )
    if test_args is None:
        return parser.parse_args()
    return parser.parse_args(test_args)


def main(test_args: list[str] | None = None) -> None:
    args = __parse_args(test_args)
    with requests.Session() as session:
        g_album = generate_albums(session)
        while True:
            print("[-] Fetching album information...")
            album = next(g_album, True)
            if isinstance(album, bool):
                break
            total_track = sum(len(tl.tracks) for tl in album.tracklists)
            print(f"[+] Found: {album.title!r} ({total_track} tracks)")
            print("[-] Downloading albums...")
            if download(album, session, save_dir=args.save_dir, overwrite=bool(args.overwrite)):
                print("[+] Done!")
            else:
                print("[!] Skipped since album already exists. (use `-o` to overwrite)")
    return print("[+] All Finished!")


if __name__ == "__main__":
    main()

__all__ = ("main",)
