import os
import logging


def custom_logger(name=None):
    """
    For consistent logger message formatting

    Args:
        name: string

    Returns:
        Logger instance
    """
    formatter = logging.Formatter(fmt="%(asctime)s - %(levelname)s - %(message)s")

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)

    try:
        logger.setLevel(os.environ["LOGGER_LEVEL"])
    except KeyError:
        logger.setLevel("INFO")

    logging.getLogger().handlers.clear()
    logger.addHandler(handler)
    return logger


class LogMessageDetails:
    def __init__(self):
        self.uid = ""
        self.request_id = ""
        self.document_templates = []
        self.matched_templates = []
        self.images_uploaded = []
        self.status = "Not Started"

    def get_info_message(self):
        return {
            "uid": self.uid,
            "request_id": self.request_id,
            "document_templates": self.document_templates,
            "matched_templates": self.matched_templates,
            "images_uploaded": self.images_uploaded,
            "status": self.status,
        }
