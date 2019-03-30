#!/usr/bin/env bash
rm ../nohup.out > /dev/null 2>&1

./kill.sh > /dev/null 2>&1
if [[ ! -f current_pid.txt ]]; then
    (cd .. && nohup venv/bin/python3 main.py) &
    echo $! > current_pid.txt
else
    echo >&2 "ERROR: already running! (current_pid.txt exists)"
    echo >&2 "Please run ./kill.sh first!"
fi
