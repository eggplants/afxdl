# afxdl

[![PyPI version](
  <https://badge.fury.io/py/afxdl.svg>
  )](
  <https://badge.fury.io/py/afxdl>
) [![Maintainability](
  <https://qlty.sh/badges/40b9ccb5-5c3b-4da1-8d07-1f2be459f004/maintainability.svg>
  )](
  <https://qlty.sh/gh/eggplants/projects/afxdl>
) [![pre-commit.ci status](
  <https://results.pre-commit.ci/badge/github/eggplants/afxdl/master.svg>
  )](
  <https://results.pre-commit.ci/latest/github/eggplants/afxdl/master>
) [![Code Coverage](
  <https://qlty.sh/badges/40b9ccb5-5c3b-4da1-8d07-1f2be459f004/test_coverage.svg>
  )](
  <https://qlty.sh/gh/eggplants/projects/afxdl>
) [![Test](
  <https://github.com/eggplants/afxdl/actions/workflows/test.yml/badge.svg>
  )](
  <https://github.com/eggplants/afxdl/actions/workflows/test.yml>
)

[![ghcr latest](
  <https://ghcr-badge.egpl.dev/eggplants/afxdl/latest_tag?trim=major&label=latest>
 ) ![ghcr size](
  <https://ghcr-badge.egpl.dev/eggplants/afxdl/size>
)](
  <https://github.com/eggplants/afxdl/pkgs/container/afxdl>
)

Download audio from <https://aphextwin.warp.net>

_Note: Redistribution of downloaded data is prohibited. Please keep it to private use._

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
[λ] === 001 ===
[-] Fetching album information...
[+] Found: 'Blackbox Life Recorder 21f / in a room7 F760' (9 tracks)
[-] Downloading albums...
[+] Saved: '/home/eggplants/Music/AphexTwin/109100-collapse-ep'
...
[λ] === 038 ===
[-] Fetching album information...
[+] All Finished!

$ tree ~/Music/AphexTwin/
/home/eggplants/Music/AphexTwin
├── 109100-collapse-ep
│   ├── 688346-t69-collapse.mp3
│   ├── 688347-1st-44.mp3
│   ├── 688348-mt1-t29r2.mp3
│   ├── 688349-abundance10edit2-r8s-fz20m-a-909.mp3
│   ├── 688350-pthex.mp3
│   └── 688351-t69-collapse-durichroma.mp3
├── 399837-blackbox-life-recorder-21f-in-a-room7-f760
...
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
