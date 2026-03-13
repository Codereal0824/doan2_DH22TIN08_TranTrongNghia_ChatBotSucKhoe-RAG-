"""
Logger Utility - Centralized logging cho toàn bộ dự án
"""
import logging
import sys
from datetime import datetime
from config.config import config

# Tạo thư mục logs nếu chưa có
if hasattr(config, 'LOGS_DIR'):
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Setup logger với format đồng nhất cho toàn dự án

    Args:
        name: Tên logger (thường là __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Get log level từ config hoặc dùng mặc định
    log_level = level or getattr(config, 'LOG_LEVEL', 'INFO')

    # Tạo logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Tránh duplicate handlers nếu logger đã được setup
    if logger.handlers:
        return logger

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Format với emoji và màu sắc
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)

    # File handler (nếu có LOGS_DIR)
    if hasattr(config, 'LOGS_DIR'):
        log_file = config.LOGS_DIR / \
            f"chatbot_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    logger.addHandler(console_handler)

    return logger


# Helper functions để dễ sử dụng
def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return setup_logger(name)


# Backward compatibility: Map print-style messages to log levels
def log_success(logger: logging.Logger, message: str):
    """Log success message (✅)"""
    logger.info(f"✅ {message}")


def log_error(logger: logging.Logger, message: str, exc_info: bool = False):
    """Log error message (❌)"""
    logger.error(f"❌ {message}", exc_info=exc_info)


def log_warning(logger: logging.Logger, message: str):
    """Log warning message (⚠️)"""
    logger.warning(f"⚠️ {message}")


def log_info(logger: logging.Logger, message: str):
    """Log info message (ℹ️)"""
    logger.info(f"ℹ️ {message}")


def log_debug(logger: logging.Logger, message: str):
    """Log debug message (🔍)"""
    logger.debug(f"🔍 {message}")


# Export
__all__ = [
    'setup_logger',
    'get_logger',
    'log_success',
    'log_error',
    'log_warning',
    'log_info',
    'log_debug'
]
