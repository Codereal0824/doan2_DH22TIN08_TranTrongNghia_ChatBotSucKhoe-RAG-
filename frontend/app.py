"""
Flask Web Application - Chatbot Tư Vấn Sức Khỏe (với Rate Limiting, Logging & SQL Database)
Giao diện web giống Gemini
"""
from backend.utils.logger import get_logger
from backend.rag.chain import HealthChatbot
from backend.auth.auth_service import AuthService
from backend.database.sql_handler import SQLHandler
from flask_limiter.util import get_remote_address
from flask_limiter import Limiter
from flask_cors import CORS
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, session, redirect, url_for
import sys
import os
from pathlib import Path
import json
import secrets

# =====================================================================
# BƯỚC 1: CẤU HÌNH ĐƯỜNG DẪN HỆ THỐNG (PYTHON PATH MANIPULATION)
# Lùi 1 cấp: frontend -> Chatbot_suckhoe
# =====================================================================
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# =====================================================================
# BƯỚC 2: KHỞI TẠO CÁC MODULE VÀ DỊCH VỤ CỐT LÕI
# =====================================================================

logger = get_logger(__name__)

# Khởi tạo đối tượng ứng dụng WSGI (Web Server Gateway Interface) bằng Flask
app = Flask(__name__)

# Thiết lập Khóa bí mật (Secret Key) để ký (sign) các cookie của Session,
# ngăn chặn các cuộc tấn công giả mạo (Session Hijacking).
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)
if not os.getenv('FLASK_SECRET_KEY'):
    logger.warning("FLASK_SECRET_KEY not set, using random key")

# Kích hoạt CORS (Cross-Origin Resource Sharing) để cho phép giao diện Frontend
# có thể gọi API Backend mà không bị trình duyệt chặn (CORS Policy).
CORS(app)

# =====================================================================
# HÀNG RÀO BẢO VỆ API (RATE LIMITING)
# =====================================================================
# Sử dụng thư viện Flask-Limiter để ngăn chặn các cuộc tấn công Từ chối Dịch vụ
# (DDoS) và Spam Request làm cạn kiệt tài nguyên gọi API LLM (Groq).
limiter = Limiter(
    app=app,
    key_func=get_remote_address,  # Nhận diện thiết bị dựa trên địa chỉ IP
    default_limits=["100 per hour"],
    storage_uri="memory://"
)

logger.info("Rate limiter initialized")

# Khởi tạo các dịch vụ (Services) theo chuẩn Dependency Injection
chatbot = None
auth_service = AuthService()

# Khởi tạo và kiểm tra kết nối với CSDL quan hệ (SQL Server) ngay khi khởi động Web
db = SQLHandler()
if db.connect():
    logger.info("SQL Database connected in Flask app!")
else:
    logger.error("Failed to connect to SQL Database!")

# Mẫu thiết kế Lazy Initialization (Khởi tạo lười biếng).
# Chỉ thực sự nạp mô hình RAG (nặng hàng trăm MB) vào RAM khi có người dùng
# nhắn tin đầu tiên, giúp tiết kiệm tài nguyên lúc Server vừa khởi động.


def get_chatbot():
    """Get or create chatbot instance"""
    global chatbot
    if chatbot is None:
        logger.info("Initializing Health Chatbot...")
        chatbot = HealthChatbot()
        logger.info("Chatbot ready!")
    return chatbot

# =====================================================================
# ĐỊNH TUYẾN GIAO DIỆN (VIEW ROUTING)
# =====================================================================


@app.route('/')
def index():
    # Kiểm tra Session xác thực (Session Validation)
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Đẩy dữ liệu động (Template Context) xuống file HTML
    return render_template('index.html',
                           username=session.get('username', 'Guest'),
                           role=session.get('role', 'USER'))


@app.route('/login', methods=['GET', 'POST'])
# Bảo vệ luồng đăng nhập khỏi tấn công Brute-force
@limiter.limit("5 per minute")
def login():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('index'))
        return render_template('login.html')

    try:
        # Hỗ trợ cả hai kiểu Payload: JSON (API) và Form Data (HTML Form)
        data = request.get_json(force=True, silent=True)
        if not data:
            data = request.form

        username = data.get('username', '').strip()
        password = data.get('password', '')

        # Gọi logic xử lý từ tầng Dịch vụ (Service Layer)
        success, message, user_info = auth_service.login_user(
            username, password)

        if success and user_info:
            # Ghi nhận trạng thái đăng nhập vào Cookie Session
            session['user_id'] = user_info['id']
            session['username'] = user_info['username']
            session['email'] = user_info['email']
            session['role'] = user_info['role']
            return jsonify({'success': True, 'message': message, 'redirect': url_for('index')})
        else:
            # Trả về HTTP Status Code 401 (Unauthorized)
            return jsonify({'success': False, 'message': message}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")  # Giới hạn tạo tài khoản rác
def register():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('index'))
        return render_template('register.html')

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            data = request.form

        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        success, message, user_id = auth_service.register_user(
            username, email, password, confirm_password)

        if success:
            return jsonify({'success': True, 'message': message, 'redirect': url_for('login')})
        else:
            return jsonify({'success': False, 'message': message}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/logout')
def logout():
    # Xóa sạch toàn bộ dữ liệu trong Cookie Session
    session.clear()
    return redirect(url_for('login'))

# =====================================================================
# API ĐIỀU KHIỂN LUỒNG (RESTful API ENDPOINTS)
# =====================================================================

# API LẤY DANH SÁCH PHIÊN CHAT (CHO SIDEBAR)


@app.route('/api/user/sessions', methods=['GET'])
def get_user_chat_sessions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        sessions = db.get_user_sessions(session['user_id'])
        return jsonify({'sessions': sessions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API LẤY LỊCH SỬ CỦA 1 PHIÊN CHAT CỤ THỂ


@app.route('/api/sessions/<session_id>/history', methods=['GET'])
def get_history(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        raw_history = db.get_chat_history(int(session_id))

        # Ánh xạ Role từ CSDL (USER/BOT) sang chuẩn Format của LLM (user/assistant)
        history = []
        for msg in raw_history:
            role = 'user' if msg['sender_type'] == 'USER' else 'assistant'
            history.append({"role": role, "content": msg['message_text']})

        return jsonify({'history': history, 'session_id': session_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# hanh dong xoa


@app.route('/api/chat/<session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    try:
        session_id_int = int(session_id)
    except ValueError:
        return jsonify({'success': False, 'error': 'Session ID không hợp lệ'}), 400

    try:
        user_sessions = db.get_user_sessions(session['user_id'])
        is_owned_session = any(
            item['session_id'] == session_id_int for item in user_sessions
        )

        if not is_owned_session:
            return jsonify({'success': False, 'error': 'Không tìm thấy đoạn chat'}), 404

        deleted = db.delete_session(session_id_int)
        if deleted:
            return jsonify({'success': True, 'message': 'Đã xóa'})

        return jsonify({'success': False, 'error': 'Không thể xóa đoạn chat'}), 500
    except Exception as e:
        logger.error(
            f"Error deleting chat session {session_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# =====================================================================
# API CHAT STREAMING (SỰ KIỆN GỬI TỪ MÁY CHỦ - SSE)
# =====================================================================


@app.route('/api/chat/stream', methods=['POST'])
@limiter.limit("20 per minute")
def chat_stream():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json(force=True, silent=True)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        bot = get_chatbot()

        # [KHẮC PHỤC LỖI TÍCH HỢP]: Phân loại và xử lý ID Phiên (Session ID)
        # Javascript ở Frontend thường sinh ra Session ID tạm thời (kiểu chuỗi String).
        # Đoạn code này kiểm tra xem ID có phải là số nguyên thực thụ từ DB không.
        # Nếu không, nó sẽ ép SQL Server tạo một Session thực thụ mới.
        is_valid_id = False
        if session_id and session_id != 'default':
            try:
                # Cố gắng ép kiểu dữ liệu
                session_id = int(session_id)
                is_valid_id = True
            except ValueError:
                # Bắt lỗi (Catch) nếu Frontend gửi ID dạng chuỗi ngẫu nhiên
                is_valid_id = False

        if not is_valid_id:
            # Sinh tên phiên tự động dựa trên 30 ký tự đầu tiên của tin nhắn
            session_name = user_message[:30] + \
                "..." if len(user_message) > 30 else user_message
            session_id = db.create_chat_session(
                session['user_id'], session_name)
            logger.info(f"Created new session with ID: {session_id}")

        # Tái cấu trúc lịch sử hội thoại từ CSDL để nạp vào Context Window của LLM
        raw_history = db.get_chat_history(session_id)

        rag_history = []
        temp_user_msg = ""
        for msg in raw_history:
            if msg['sender_type'] == 'USER':
                temp_user_msg = msg['message_text']
            elif msg['sender_type'] == 'BOT' and temp_user_msg:
                rag_history.append((temp_user_msg, msg['message_text']))
                temp_user_msg = ""

        # Ghi nhận ngay lập tức tin nhắn của User vào DB
        db.save_chat_message(session_id, 'USER', user_message)

        # Hàm Generator dùng cho giao thức Server-Sent Events (SSE)
        def generate():
            try:
                full_answer = ""
                # Phát (Yield) ID chuẩn xác về Frontend để đồng bộ luồng
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

                # Duyệt qua từng Chunk (Mảnh văn bản) được nhả về từ RAG Pipeline
                for chunk in bot.rag_chain.ask_stream(
                    question=user_message,
                    # Giới hạn bộ nhớ ngắn hạn: 10 tin nhắn gần nhất
                    chat_history=rag_history[-10:],
                    return_sources=True
                ):
                    full_answer += chunk
                    # Bắn ngay chunk vừa nhận được qua HTTP Connection đang mở
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

                # Kỹ thuật bóc tách Nguồn (Source Parsing) bằng chuỗi ở bước hậu kỳ
                sources = []
                if "Nguồn:" in full_answer:
                    parts = full_answer.split("Nguồn:")
                    sources_text = parts[1].strip()
                    sources = [s.strip()
                               for s in sources_text.split(',') if s.strip()]
                    if sources:
                        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

                # Ghi nhận toàn bộ văn bản hoàn chỉnh của AI vào DB
                db.save_chat_message(session_id, 'BOT', full_answer)

                # Phát tín hiệu kết thúc luồng (End of Stream)
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                logger.error(
                    f"Error in stream generation: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        # Đóng gói Generator thành một Response Stream với Mimetype đặc thù 'text/event-stream'
        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    except Exception as e:
        logger.error(f"Error in chat_stream endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


# Khởi động máy chủ phát triển (Development Server)
if __name__ == '__main__':
    print("=" * 70)
    print("CHATBOT SUC KHOE - WEB APPLICATION (SQL DATABASE)")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)
