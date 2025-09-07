﻿import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

def setup_logging(level: int = logging.INFO):
    logging.basicConfig(level=level, format=LOG_FORMAT)
    return logging.getLogger("ameth")
