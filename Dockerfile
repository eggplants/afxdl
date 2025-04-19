FROM python:3

ARG VERSION
ENV VERSION ${VERSION:-master}

LABEL maintainer="eggplants <w10776e8w@yahoo.co.jp>"
LABEL description="Download audio from aphextwin.warp.net"

RUN useradd --create-home appuser
WORKDIR /home/appuser
USER appuser

RUN pip install --upgrade pip

RUN python -m pip install git+https://github.com/eggplants/afxdl@${VERSION}

ENTRYPOINT ["afxdl"]
