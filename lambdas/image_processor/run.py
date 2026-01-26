# usage: LOGGER_LEVEL=DEBUG PYTHONPATH=. python run.py $ABS_PATH_TO_SCAN $TEMPLATE_TYPE

import datetime
import os
import pytest
from unittest.mock import patch
from app.handler import ImageProcessor
from app.utility.extraction_service import ExtractionService
from app.utility.bucket_manager import ScanLocationStore, ScanLocation
from app.utility.custom_logging import LogMessageDetails
import sys

def run(path, template):
    extraction_service = ExtractionService(
        extraction_folder_path="extraction",
        folder_name="./folder",
        output_folder_path="./out",
        info_msg=LogMessageDetails(),
    )

    scan_locations = ScanLocationStore()
    
    scan_locations.add_scan(
        ScanLocation(
            location=path,
            template=template,
        )
    )
    
    continuation_keys_to_use = extraction_service.run_iap_extraction(scan_locations)
    print(continuation_keys_to_use)

run(sys.argv[1], sys.argv[2])
