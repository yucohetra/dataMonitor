import logging
from logging import Logger


def configure_logging() -> Logger:
    """
    Configures application-level logging.

    Design considerations:
    - Uses a consistent log format for easier troubleshooting.
    - Keeps configuration minimal and deterministic for evaluation environments.
    """
    logger = logging.getLogger("realtime-monitoring")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s %(name)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
