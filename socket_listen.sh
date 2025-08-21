#!/bin/bash
LISTEN_PORT=$1

if [ -z $LISTEN_PORT ]; then
    echo "Please add argument to listen port - example socket.sh 7985"
    exit 1
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

socat TCP4-LISTEN:$LISTEN_PORT,fork,tcpwrap=script EXEC:$SCRIPT_DIR/socket.sh