from src.config import LOG_DIR

import logging
import os
from datetime import datetime
import pytz


def converter(timestamp):
    dt = datetime.fromtimestamp(timestamp, tz=pytz.utc)
    return dt.astimezone(pytz.timezone("US/Eastern")).timetuple()


formatter = logging.Formatter(
    "%(asctime)s - %(name)s:%(levelname)s: %(filename)s:%(lineno)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
formatter.converter = converter


def get_file_handler(log_dir=LOG_DIR):
    """
    Returns a file handler for logging.
    """
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d")
    file_name = f"codesearch_{timestamp}.log"
    file_handler = logging.FileHandler(os.path.join(log_dir, file_name))
    file_handler.setFormatter(formatter)
    return file_handler


def get_console_handler():
    """
    Returns a console handler for logging.
    """
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    return console_handler


# Configure the base logger
base_logger = logging.getLogger()
base_logger.setLevel(logging.INFO)
base_logger.addHandler(get_file_handler())
base_logger.addHandler(get_console_handler())


def set_log_level(level=logging.INFO):
    """
    Sets the logging level for the base logger.
    """
    base_logger.setLevel(level)
    for handler in base_logger.handlers:
        handler.setLevel(level)


def configure_uvicorn_logger():
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    # Remove existing handlers to avoid duplicate logging
    uvicorn_error_logger.handlers.clear()
    uvicorn_error_logger.addHandler(get_file_handler())
    uvicorn_error_logger.addHandler(get_console_handler())
