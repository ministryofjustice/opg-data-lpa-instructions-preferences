import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    message = 'Hello World'
    logger.info(message)

    return message
