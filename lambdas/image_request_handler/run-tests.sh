#!/bin/bash

set -oe pipefail

coverage run --source /lambdas/image_request_handler/app -m pytest /lambdas/image_request_handler/tests/

coverage report
