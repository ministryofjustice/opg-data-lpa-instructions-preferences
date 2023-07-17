#!/bin/bash

set -eo pipefail

coverage run --source /function/app -m pytest /function/tests/

coverage report
