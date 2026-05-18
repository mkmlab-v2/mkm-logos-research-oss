# MKM Cloud Agent base image — system deps only (Cursor checks out the repo).
# Do not COPY the project; see https://cursor.com/docs/cloud-agent/setup

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/ubuntu
