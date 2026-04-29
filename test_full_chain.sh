#!/bin/bash
poetry run drova_test_poll &

DROVA_TEST_POLL_PID=$!
sleep 1

curl -v http://localhost:8000/set_desktop_new

sleep 30

curl -v http://localhost:8000/set_session_active

read -p "Press enter to continue" test

curl -v http://localhost:8000/set_session_finished

sleep 30

kill $DROVA_TEST_POLL_PID