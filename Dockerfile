FROM ubuntu:latest
LABEL authors="sanyo"

ENTRYPOINT ["top", "-b"]