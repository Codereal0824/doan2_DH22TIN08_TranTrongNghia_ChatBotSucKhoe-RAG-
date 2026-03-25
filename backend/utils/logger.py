"""
Logger Utility - Centralized logging cho toàn bộ dự án
"""
import logging
import sys
from datetime import datetime
from config.config import config

# Tạo thư mục logs tự động nếu chưa tồn tại trên hệ điều hành.
# Việc lưu log ra file vật lý (File I/O) rất quan trọng để giám sát
# hoạt động của server và truy vết lỗi (Troubleshooting) sau khi deploy.
if hasattr(config, 'LOGS_DIR'):
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Hàm thiết lập (Setup) bộ ghi nhật ký cấu hình chuẩn.
# Sử dụng mẫu thiết kế Singleton ngầm định của thư viện logging:
# Cùng một 'name' sẽ luôn trả về cùng một instance của Logger.


def setup_logger(name: str, level: str = None) -> logging.Logger:
    """
    Setup logger với format đồng nhất cho toàn dự án

    Args:
        name: Tên logger (thường là __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Trích xuất cấu hình Cấp độ Log (Log Level) từ biến môi trường.
    # Giúp dễ dàng chuyển đổi giữa môi trường Phát triển (DEBUG) và Sản xuất (INFO/WARNING)
    # mà không cần sửa code.
    log_level = level or getattr(config, 'LOG_LEVEL', 'INFO')

    # Khởi tạo đối tượng Logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Ngăn chặn hiện tượng Nhân bản Log (Duplicate Handlers).
    # Xảy ra khi một module được import nhiều lần khiến log bị in ra màn hình lặp đi lặp lại.
    if logger.handlers:
        return logger

    # 1. Console Handler: Xử lý luồng xuất dữ liệu ra màn hình Terminal (stdout).
    # Hỗ trợ quá trình phát triển và theo dõi trực tiếp thời gian thực.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Định dạng (Formatter) cho luồng Console: Tinh gọn, dễ đọc.
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)

    # 2. File Handler: Xử lý luồng ghi dữ liệu xuống ổ cứng.
    # Áp dụng cơ chế Rotating Log cơ bản (Tạo file log mới mỗi ngày).
    if hasattr(config, 'LOGS_DIR'):
        log_file = config.LOGS_DIR / \
            f"chatbot_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # Định dạng cho luồng File: Chi tiết hơn, bao gồm cả tên hàm (funcName)
        # và số dòng (lineno) để phục vụ việc debug ngoại tuyến (Offline Debugging).
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    logger.addHandler(console_handler)

    return logger


# Hàm tiện ích (Helper function) dùng để bọc gọn thao tác khởi tạo
def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger

    Args:
        name: Logger name

    Returns:
        logging.Logger: Logger instance
    """
    return setup_logger(name)


# ============================================
# CÁC HÀM TIỆN ÍCH GHI LOG CÓ GẮN THẺ (TAGGING)
# Hỗ trợ backward compatibility với phong cách print cũ nhưng chuyên nghiệp hơn.
# ============================================

def log_success(logger: logging.Logger, message: str):
    """Log success message"""
    logger.info(f"[THANH CONG] {message}")


def log_error(logger: logging.Logger, message: str, exc_info: bool = False):
    """
    Log error message
    Tham số exc_info=True cho phép in toàn bộ Call Stack (Traceback) của lỗi,
    rất hữu ích khi bắt các Exception hệ thống.
    """
    logger.error(f"[LOI] {message}", exc_info=exc_info)


def log_warning(logger: logging.Logger, message: str):
    """Log warning message"""
    logger.warning(f"[CANH BAO] {message}")


def log_info(logger: logging.Logger, message: str):
    """Log info message"""
    logger.info(f"[THONG TIN] {message}")


def log_debug(logger: logging.Logger, message: str):
    """Log debug message"""
    logger.debug(f"[CHI TIET] {message}")


# Xuất các hàm công khai (Public API) của module
__all__ = [
    'setup_logger',
    'get_logger',
    'log_success',
    'log_error',
    'log_warning',
    'log_info',
    'log_debug'
]
