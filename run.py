"""
Script khởi động chatbot - Chạy file này thay vì frontend/app.py
"""
from frontend.app import app
import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import và chạy Flask app

if __name__ == '__main__':
    print("=" * 70)
    print("🏥 CHATBOT SỨC KHỎE - WEB APPLICATION")
    print("=" * 70)
    print()
    print("⏳ Starting Flask server...")
    print("🌐 Server will run at: http://localhost:5000")
    print("📱 Open browser and visit: http://localhost:5000")
    print()
    print("💡 Press Ctrl+C to stop server")
    print()

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
