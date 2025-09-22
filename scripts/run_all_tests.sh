#!/usr/bin/env bash
set -euo pipefail

python3 -m pytest -m "not slow"
python3 -m pytest -m acceptance
python3 -m pytest -m contracts
python3 -m pytest -m resilience
