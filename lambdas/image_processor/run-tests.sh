#!/bin/bash

set -oe pipefail

coverage run --source /function/app -m pytest /function/tests/

cat thisshouldfail

coverage report
