# # Log to stdout in JSON format
# export FUSELINE_LOG_LEVEL=DEBUG
# export FUSELINE_LOG_OUTPUT=stdout
# export FUSELINE_LOG_FORMAT=json

# # Log to both stderr and file in human-readable format
# export FUSELINE_LOG_LEVEL=INFO
# export FUSELINE_LOG_OUTPUT=both
# export FUSELINE_LOG_FORMAT=human
# export FUSELINE_LOG_FILE=my_custom_log.txt

# # Log to file in JSON format
# export FUSELINE_LOG_LEVEL=WARNING
# export FUSELINE_LOG_OUTPUT=file
# export FUSELINE_LOG_FORMAT=json
# export FUSELINE_LOG_FILE=my_json_log.json


import os
import sys
import json
from loguru import logger
from datetime import datetime


class JsonFormatter:
    def __call__(self, record):
        log_record = {
            "time": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
            "process": record["process"].name,
            "thread": record["thread"].name,
            "extra": record["extra"],
        }

        if record["exception"] is not None:
            log_record["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback,
            }

        return json.dumps(log_record)


def setup_logger():
    """Set up the logger based on environment variables."""
    # Remove any existing handlers
    logger.remove()

    # Check if logging should be disabled
    if os.environ.get("FUSELINE_DISABLE_LOGGING", "").lower() in ["true", "1", "yes"]:
        # Disable all logging
        logger.disable("fuseline")
        return

    # Get log level from environment variable, default to INFO
    log_level = os.environ.get("FUSELINE_LOG_LEVEL", "").upper()
    if not log_level:
        # Disable all logging
        logger.disable("fuseline")
        return

    # Get log output destination from environment variable, default to stderr
    log_output = os.environ.get("FUSELINE_LOG_OUTPUT", "stderr").lower()

    # Get log format from environment variable, default to human
    log_format = os.environ.get("FUSELINE_LOG_FORMAT", "human").lower()

    # Human-readable format
    human_format = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

    # Configure outputs
    if log_output in ["stdout", "both"]:
        if log_format == "json":
            logger.add(sys.stdout, serialize=True, format=JsonFormatter(), level=log_level)
        else:
            logger.add(sys.stdout, format=human_format, level=log_level)

    if log_output in ["stderr", "both"]:
        if log_format == "json":
            logger.add(sys.stderr, serialize=True, format=JsonFormatter(), level=log_level)
        else:
            logger.add(sys.stderr, format=human_format, level=log_level)

    if log_output in ["file", "both"]:
        log_file = os.environ.get("FUSELINE_LOG_FILE", "fuseline.log")
        if log_format == "json":
            logger.add(log_file, serialize=True, format=JsonFormatter(), level=log_level)
        else:
            logger.add(log_file, format=human_format, level=log_level)


def get_logger():
    """Get the configured logger."""
    return logger


# Set up the logger when this module is imported
setup_logger()
