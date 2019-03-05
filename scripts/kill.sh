#!/usr/bin/env bash

if [[ ! -f current_pid.txt ]]; then
    echo >&2 "ERROR: no current_pid.txt found. abort."
else
    kill -9 `cat current_pid.txt` > /dev/null 2>&1
    rm current_pid.txt > /dev/null 2>&1
    echo "killed."
fi