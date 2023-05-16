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
    logger_name = name if name else "lpa_code_generator"
    formatter = logging.Formatter(
        fmt=f"%(asctime)s - %(levelname)s - {logger_name} - in %("
        f"funcName)s:%(lineno)d - %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)

    try:
        logger.setLevel(os.environ["LOGGER_LEVEL"])
    except KeyError:
        logger.setLevel("INFO")
    logger.addHandler(handler)
    return logger


class LogMessageDetails:
    def __init__(self):
        self.uid = ""
        self.document_paths = {}
        self.matched_templates = []
        self.images_uploaded = []
        self.status = "Not Started"

    def get_info_message(self):
        return {
            "uid": self.uid,
            "document_paths": self.document_paths,
            "matched_templates": self.matched_templates,
            "images_uploaded": self.images_uploaded,
            "status": self.status,
        }
