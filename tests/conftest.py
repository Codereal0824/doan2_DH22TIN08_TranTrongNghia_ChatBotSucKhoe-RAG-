import sys
from pathlib import Path

# Thêm thư mục gốc của project vào sys.path để test scripts có thể import backend
sys.path.insert(0, str(Path(__file__).parent.parent))
