"""
Centralised logging configuration.
"""

import logging
import logging.handlers
import sys
import json
from datetime import datetime

def setup_logger(name, level_str):
    level = getattr(logging, level_str.upper(), logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler
    fh = logging.handlers.RotatingFileHandler(
        LOGGING['file'], maxBytes=LOGGING['max_bytes'], backupCount=LOGGING['backup_count']
    )
    fh.setLevel(level)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

# Create a root logger
log = setup_logger('trading_bot', LOGGING['level'])
