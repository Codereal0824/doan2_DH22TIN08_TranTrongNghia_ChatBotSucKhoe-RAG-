"""
Flask Web Application - Chatbot Tư Vấn Sức Khỏe (với Rate Limiting, Logging & SQL Database)
Giao diện web giống Gemini
"""
from backend.utils.logger import get_logger
from config.config import config
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
import time
import secrets

# =====================================================================
# BƯỚC 1: ÉP PYTHON TÌM THƯ MỤC GỐC TRƯỚC TIÊN (BẮT BUỘC NẰM TRÊN CÙNG)
# Lùi 1 cấp: frontend -> Chatbot_suckhoe
# =====================================================================
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# =====================================================================
# BƯỚC 2: IMPORT CÁC MODULE CỦA DỰ ÁN
# =====================================================================

logger = get_logger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Secret key - load from env or generate
app.secret_key = os.getenv('FLASK_SECRET_KEY') or secrets.token_hex(32)
if not os.getenv('FLASK_SECRET_KEY'):
    logger.warning("⚠️ FLASK_SECRET_KEY not set, using random key")

CORS(app)

# Initialize Rate Limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://"
)

logger.info("✅ Rate limiter initialized")

# Initialize services
chatbot = None
auth_service = AuthService()

# KHỞI TẠO KẾT NỐI DATABASE
db = SQLHandler()
if db.connect():
    logger.info("✅ SQL Database connected in Flask app!")
else:
    logger.error("❌ Failed to connect to SQL Database!")


def get_chatbot():
    """Get or create chatbot instance"""
    global chatbot
    if chatbot is None:
        logger.info("🚀 Initializing Health Chatbot...")
        chatbot = HealthChatbot()
        logger.info("✅ Chatbot ready!")
    return chatbot


@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html',
                           username=session.get('username', 'Guest'),
                           role=session.get('role', 'USER'))


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if request.method == 'GET':
        if 'user_id' in session:
            return redirect(url_for('index'))
        return render_template('login.html')

    try:
        data = request.get_json(force=True, silent=True)
        if not data:
            data = request.form

        username = data.get('username', '').strip()
        password = data.get('password', '')

        success, message, user_info = auth_service.login_user(
            username, password)

        if success and user_info:
            session['user_id'] = user_info['id']
            session['username'] = user_info['username']
            session['email'] = user_info['email']
            session['role'] = user_info['role']
            return jsonify({'success': True, 'message': message, 'redirect': url_for('index')})
        else:
            return jsonify({'success': False, 'message': message}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per minute")
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
    session.clear()
    return redirect(url_for('login'))


# ==========================================
# API LẤY DANH SÁCH PHIÊN CHAT (CHO SIDEBAR)
# ==========================================
@app.route('/api/user/sessions', methods=['GET'])
def get_user_chat_sessions():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        sessions = db.get_user_sessions(session['user_id'])
        return jsonify({'sessions': sessions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
# API LẤY LỊCH SỬ CỦA 1 PHIÊN CHAT CỤ THỂ
# ==========================================
@app.route('/api/sessions/<session_id>/history', methods=['GET'])
def get_history(session_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    try:
        raw_history = db.get_chat_history(int(session_id))

        history = []
        for msg in raw_history:
            role = 'user' if msg['sender_type'] == 'USER' else 'assistant'
            history.append({"role": role, "content": msg['message_text']})

        return jsonify({'history': history, 'session_id': session_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==========================================
# API CHAT STREAMING (NÂNG CẤP LƯU DATABASE)
# ==========================================
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

        # ====================================================
        # ĐÃ FIX: Xử lý session_id dạng chuỗi từ Frontend sinh ra
        # ====================================================
        is_valid_id = False
        if session_id and session_id != 'default':
            try:
                # Cố gắng ép thành số nguyên (INT)
                session_id = int(session_id)
                is_valid_id = True
            except ValueError:
                # Nếu Frontend gửi chữ (như 'session_17733...'), nó sẽ văng lỗi vào đây
                is_valid_id = False

        if not is_valid_id:
            # Tạo session mới đàng hoàng trong Database
            session_name = user_message[:30] + \
                "..." if len(user_message) > 30 else user_message
            session_id = db.create_chat_session(
                session['user_id'], session_name)
            logger.info(f"Created new session with ID: {session_id}")
        # ====================================================

        raw_history = db.get_chat_history(session_id)

        rag_history = []
        temp_user_msg = ""
        for msg in raw_history:
            if msg['sender_type'] == 'USER':
                temp_user_msg = msg['message_text']
            elif msg['sender_type'] == 'BOT' and temp_user_msg:
                rag_history.append((temp_user_msg, msg['message_text']))
                temp_user_msg = ""

        db.save_chat_message(session_id, 'USER', user_message)

        def generate():
            try:
                full_answer = ""
                # Gửi ID xịn bằng số nguyên về lại cho Frontend cập nhật
                yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"

                for chunk in bot.rag_chain.ask_stream(
                    question=user_message,
                    chat_history=rag_history[-10:],
                    return_sources=True
                ):
                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

                sources = []
                if "📚 Nguồn:" in full_answer:
                    parts = full_answer.split("📚 Nguồn:")
                    sources_text = parts[1].strip()
                    sources = [s.strip()
                               for s in sources_text.split(',') if s.strip()]
                    if sources:
                        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

                db.save_chat_message(session_id, 'BOT', full_answer)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                logger.error(
                    f"❌ Error in stream generation: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return Response(stream_with_context(generate()), mimetype='text/event-stream')

    except Exception as e:
        logger.error(f"❌ Error in chat_stream endpoint: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 70)
    print("🏥 CHATBOT SỨC KHỎE - WEB APPLICATION (SQL DATABASE)")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)
