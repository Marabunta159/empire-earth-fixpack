#!/bin/bash
# usage: ui.sh <shotname> <sleep> cmd...   -> sends WinDrive commands to the sandbox game, waits, takes a screenshot
name="$1"; slp="$2"; shift 2
P="${EEPROC:-Empire Earth}"
if [ $# -gt 0 ]; then um win drive --proc "$P" "focus" "$@" 2>&1 | tail -1; fi
sleep "$slp"
um win drive --proc "$P" "focus" >/dev/null 2>&1
um win shot --exe "$P.exe" "shots/$name.png" --scale 0.4 2>&1 | grep -v _small | tail -1
