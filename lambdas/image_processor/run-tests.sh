#!/bin/bash

set -o pipefail

coverage run --source /function/app -m pytest /function/tests/

coverage report
