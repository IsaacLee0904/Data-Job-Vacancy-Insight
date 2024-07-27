import os
import sys
import logging
from logging.handlers import RotatingFileHandler

def set_logger(level=logging.INFO):
    """
    Set up and initialize the logger based on the current script name.
    
    Returns:
    - logger: logging.Logger
        Configured logger instance.
    """
    # Get the current script name (without file extension)
    script_name = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    # Create log file path
    log_directory = "/app/logs"  # Adjust the log directory path according to your Docker volume setup
    if not os.path.exists(log_directory):
        os.makedirs(log_directory)
    log_file_path = os.path.join(log_directory, f"{script_name}.log")

    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    # File handler for logs
    file_handler = RotatingFileHandler(log_file_path, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(level)
    file_format = logging.Formatter('%(asctime)s %(levelname)s - %(filename)s:%(lineno)d - %(message)s', datefmt='%Y-%m-%dT%H:%M:%S%z')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)

    # Console handler for logs
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter('%(asctime)s %(levelname)s - %(message)s', datefmt='%Y-%m-%dT%H:%M:%S%z')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    return logger
