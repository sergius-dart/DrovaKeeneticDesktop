#!/bin/bash
source .env

poetry run python before_connect.py
RESULT_BEFORE_CONNECT=$?

socat - TCP4:${WINDOWS_HOST}:7985

if [[ $RESULT_BEFORE_CONNECT -eq 0 ]]; then
    poetry run python after_disconnect.py
fi