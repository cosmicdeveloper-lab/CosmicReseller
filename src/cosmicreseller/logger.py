# src/cosmicreseller/utils/logger.py

import logging


def configure_root_logger(level=logging.INFO):
    """
    Set up root logger with stream (console) output.
    """
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
