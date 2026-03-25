"""
Script khởi động chatbot - Chạy file này thay vì frontend/app.py
"""
from frontend.app import app
import sys
from pathlib import Path

# =====================================================================
# THIẾT LẬP MÔI TRƯỜNG THỰC THI (RUNTIME ENVIRONMENT SETUP)
# =====================================================================
# Xác định đường dẫn tuyệt đối của thư mục gốc dự án.
project_root = Path(__file__).parent

# Chèn thư mục gốc vào vị trí ưu tiên cao nhất (index 0) trong danh sách
# đường dẫn tìm kiếm module của trình thông dịch Python (sys.path).
# Điều này giải quyết triệt để lỗi "ModuleNotFoundError" khi các tệp tin
# nằm sâu trong các gói (packages) như 'backend' hay 'frontend' cố gắng import chéo nhau.
sys.path.insert(0, str(project_root))

# Kỹ thuật Deferred Import (Import trì hoãn):
# Chỉ import đối tượng 'app' của Flask SAU KHI đã cấu hình xong sys.path.

# =====================================================================
# ĐIỂM VÀO ỨNG DỤNG (APPLICATION ENTRY POINT)
# =====================================================================
# Câu lệnh điều kiện này đảm bảo rằng máy chủ Web chỉ được khởi động
# khi tệp này được thực thi trực tiếp bằng lệnh "python run.py",
# chứ không bị vô tình chạy nếu tệp này bị một module khác import vào.
if __name__ == '__main__':
    print("=" * 70)
    print("[HE THONG] CHATBOT SUC KHOE - WEB APPLICATION")
    print("=" * 70)
    print()
    print("[TIEN TRINH] Starting Flask server...")
    print("[THONG TIN] Server will run at: http://localhost:5000")
    print("[HUONG DAN] Open browser and visit: http://localhost:5000")
    print()
    print("[LENH] Press Ctrl+C to stop server")
    print()

    # Kích hoạt máy chủ WSGI tích hợp sẵn của thư viện Werkzeug (đi kèm Flask).
    app.run(
        # host='0.0.0.0': Chỉ định máy chủ lắng nghe trên tất cả các giao diện mạng (All Network Interfaces).
        # Điều này cho phép các thiết bị khác trong cùng mạng LAN (như điện thoại, laptop khác)
        # hoặc môi trường Container (Docker) có thể truy cập được vào ứng dụng thông qua địa chỉ IP của máy chủ.
        host='0.0.0.0',
        port=5000,

        # debug=True: Kích hoạt chế độ gỡ lỗi.
        # Cung cấp tính năng Hot-reloading (tự động khởi động lại server khi lưu file code)
        # và hiển thị Stack Trace chi tiết trên trình duyệt nếu có lỗi (Exception) xảy ra.
        # [CANH BAO]: Tuyệt đối phải chuyển thành False khi đưa lên môi trường Production.
        debug=True
    )
