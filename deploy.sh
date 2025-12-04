#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

rsync -av *.py bpim2plus:ledcylinder_server
ssh bpim2plus systemctl --user restart ledcylinder

