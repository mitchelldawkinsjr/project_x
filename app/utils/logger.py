"""Logging utility"""
import logging
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("reddit_viewer")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance"""
    if name:
        return logging.getLogger(f"reddit_viewer.{name}")
    return logger

