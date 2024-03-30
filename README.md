# afxdl

[![PyPI version](
  <https://badge.fury.io/py/afxdl.svg>
  )](
  <https://badge.fury.io/py/afxdl>
) [![Maintainability](
  <https://api.codeclimate.com/v1/badges/61cf398cfd4818652b13/maintainability>
  )](
  <https://codeclimate.com/github/eggplants/afxdl/maintainability>
) [![pre-commit.ci status](
  <https://results.pre-commit.ci/badge/github/eggplants/afxdl/master.svg>
  )](
  <https://results.pre-commit.ci/latest/github/eggplants/afxdl/master>
) [![Test Coverage](
  <https://api.codeclimate.com/v1/badges/61cf398cfd4818652b13/test_coverage>
  )](
  <https://codeclimate.com/github/eggplants/afxdl/test_coverage>
) [![Test](
  <https://github.com/eggplants/afxdl/actions/workflows/test.yml/badge.svg>
  )](
  <https://github.com/eggplants/afxdl/actions/workflows/test.yml>
)

[![ghcr latest](
  <https://ghcr-badge.deta.dev/eggplants/afxdl/latest_tag?trim=major&label=latest>
 ) ![ghcr size](
  <https://ghcr-badge.deta.dev/eggplants/afxdl/size>
)](
  <https://github.com/eggplants/afxdl/pkgs/container/afxdl>
)

Download audio from <https://aphextwin.warp.net>

## Install

```bash
pip install afxdl
```

OR:

```bash
pipx install afxdl
```

## Run

```shellsession
$ afxdl ~/Music/AphexTwin
[-] Fetching album information...
[+] Found: 'Blackbox Life Recorder 21f / in a room7 F760' (9 tracks)
[-] Downloading albums...
[+] Done!
...
[-] Fetching album information...
[+] All Finished!
```

## Help

```shellsession
$ afxdl -h
usage: afxdl [-h] [-o] [-V] [save_dir]

download audio from <aphextwin.warp.net>

positional arguments:
  save_dir         directory to save albums (default: ./AphexTwin/)

options:
  -h, --help       show this help message and exit
  -o, --overwrite  overwrite saved albums (default: False)
  -V, --version    show program's version number and exit
```
