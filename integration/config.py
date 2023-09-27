# Setup Data

environment = {
    "local": {
        "sirius_url": "http://localhost:4566",
        "sirius_bucket": "opg-backoffice-datastore-local",
        "iap_bucket": "lpa-iap",
    },
    "development": {
        "sirius_url": "http://api.integration.ecs",
        "sirius_bucket": "opg-backoffice-datastore-integration",
        "iap_bucket": "lpa-iap",
    },
}

templates = {
    "LP1H": {
        "lpa_uid": "700000000047",
        "expected_collection_started_response": {
            "uId": "700000000047",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000047",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000047",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000047-instructions": "",
                "iap-700000000047-preferences": "",
            },
        },
    },
    "LP1F": {
        "lpa_uid": "700000000138",
        "expected_collection_started_response": {
            "uId": "700000000138",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000138",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000138",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000138-instructions": "",
                "iap-700000000138-preferences": "",
                "iap-700000000138-continuation_instructions_1": "",
                "iap-700000000138-continuation_instructions_2": "",
                "iap-700000000138-continuation_preferences_1": "",
            },
        },
    },
    "PFA117": {
        "lpa_uid": "700000000088",
        "expected_collection_started_response": {
            "uId": "700000000088",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000088",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000088",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000088-instructions": "",
                "iap-700000000088-preferences": "",
            },
        },
    },
    "HW114": {
        "lpa_uid": "700000000089",
        "expected_collection_started_response": {
            "uId": "700000000089",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000089",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000089",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000089-instructions": "",
                "iap-700000000089-preferences": "",
                "iap-700000000089-continuation_unknown_1": "",
                "iap-700000000089-continuation_unknown_2": "",
            },
        },
    },
    "LPA_PW": {
        "lpa_uid": "700000000090",
        "expected_collection_started_response": {
            "uId": "700000000090",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000090",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000090",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000090-instructions": "",
                "iap-700000000090-preferences": "",
            },
        },
    },
    "LP1F_LP": {
        "lpa_uid": "700000000091",
        "expected_collection_started_response": {
            "uId": "700000000091",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000091",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000091",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000091-instructions": "",
                "iap-700000000091-preferences": "",
                "iap-700000000091-continuation_preferences_1": "",
            },
        },
    },
    "LP1F-continuation-broken-barcode": {
        "lpa_uid": "700000000094",
        "expected_collection_started_response": {
            "uId": "700000000094",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000094",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000094",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000094-instructions": "",
                "iap-700000000094-preferences": "",
                "iap-700000000094-continuation_instructions_1": "",
                "iap-700000000094-continuation_preferences_1": "",
            },
        },
    },
    "LP1F-continuation-working-barcode": {
        "lpa_uid": "700000000095",
        "expected_collection_started_response": {
            "uId": "700000000095",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000095",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000095",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000095-instructions": "",
                "iap-700000000095-preferences": "",
                "iap-700000000095-continuation_instructions_1": "",
                "iap-700000000095-continuation_preferences_1": "",
            },
        },
    },
    "LP1F-prefsonly-continuation-broken-barcode": {
        "lpa_uid": "700000000096",
        "expected_collection_started_response": {
            "uId": "700000000096",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000096",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000096",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000096-preferences": "",
                "iap-700000000096-instructions": "",
                "iap-700000000096-continuation_preferences_1": "",
                "iap-700000000096-continuation_preferences_2": "",
                "iap-700000000096-continuation_preferences_3": "",
            },
        },
    },
    "LP1F-prefsonly-continuation-working-barcode": {
        "lpa_uid": "700000000097",
        "expected_collection_started_response": {
            "uId": "700000000097",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000097",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000097",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000097-preferences": "",
                "iap-700000000097-instructions": "",
                "iap-700000000097-continuation_instructions_1": "",
                "iap-700000000097-continuation_preferences_1": "",
                "iap-700000000097-continuation_preferences_2": "",
                "iap-700000000097-continuation_preferences_3": "",
            },
        },
    },
    "LP1F-tiff-file": {
        "lpa_uid": "700000000093",
        "expected_collection_started_response": {
            "uId": "700000000093",
            "status": "COLLECTION_NOT_STARTED",
            "signedUrls": {},
        },
        "expected_collection_in_progress_response": {
            "uId": "700000000093",
            "status": "COLLECTION_IN_PROGRESS",
            "signedUrls": {},
        },
        "expected_collection_completed_response": {
            "uId": "700000000093",
            "status": "COLLECTION_COMPLETE",
            "signedUrls": {
                "iap-700000000093-preferences": "",
                "iap-700000000093-instructions": "",
                "iap-700000000093-continuation_instructions_1": "",
                "iap-700000000093-continuation_preferences_1": "",
            },
        },
    },
}
