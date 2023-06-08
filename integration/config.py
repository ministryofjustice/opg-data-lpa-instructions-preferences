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
}
