# Setup Data

environment = {
    'local': {
        "sirius_url": "http://localhost:4566",
        "sirius_bucket": "opg-backoffice-datastore-local",
        "iap_bucket": "lpa-iap"
    },
    'development': {
        "sirius_url": "http://api.integration.ecs",
        "sirius_bucket": "opg-backoffice-datastore-integration",
        "iap_bucket": "lpa-iap"
    }
}

templates = {
    "LP1H_New": {
        "lpa_uid": "700000000047",
        "expected_collection_started_response": {
            "uid": "700000000047",
            "status": "COLLECTION_NOT_STARTED",
            "signed_urls": {
                "iap-700000000047-instructions": "",
                "iap-700000000047-preferences": "",
                "iap-700000000047-continuation-instructions": "",
                "iap-700000000047-continuation-preferences": ""
            }
        },
        "expected_collection_in_progress_response": {
            "uid": "700000000047",
            "status": "COLLECTION_IN_PROGRESS",
            "signed_urls": {
                "iap-700000000047-instructions": "",
                "iap-700000000047-preferences": "",
                "iap-700000000047-continuation-instructions": "",
                "iap-700000000047-continuation-preferences": ""
            }
        },
        "expected_collection_completed_response": {
            "uid": "700000000047",
            "status": "COLLECTION_COMPLETE",
            "signed_urls": {
                "iap-700000000047-instructions": "",
                "iap-700000000047-preferences": "",
                "iap-700000000047-continuation-instructions": "",
                "iap-700000000047-continuation-preferences": ""
            }
        },
    },
    # "LP1F_New": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
    # "LP1H_Large_Print": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
    # "LP1F_Large_Print": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
    # "LP1H_Old": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
    # "LP1F_Old": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
    # "LP1H_Older": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
    # "LP1F_Older": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
    # "LP1H_Correspondence": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
    # "LP1F_Correspondence": {
    #     "lpa_uid": "700000000048",
    #     "sirius_url": sirius_url
    # },
}
