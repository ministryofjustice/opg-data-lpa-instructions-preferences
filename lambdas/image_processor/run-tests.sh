#!/bin/bash

set -oe pipefail

python -m coverage run --source /function/app --module pytest /function/tests/

python -m coverage report
