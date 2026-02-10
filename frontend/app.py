"""
Flask Web Application - Chatbot Tư Vấn Sức Khỏe
Giao diện web giống Gemini
"""
from config.config import config
from backend.rag.chain import HealthChatbot
from backend.auth.auth_service import AuthService
from backend.auth.decorators import login_required, logout_required
from flask import Flask, render_template, request, jsonify, Response, stream_with_context, session, redirect, url_for, flash
from flask_cors import CORS
import sys
from pathlib import Path
import json
import time
import secrets

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))


# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(32)  # Secret key cho session
CORS(app)  # Enable CORS for API requests

# Initialize auth service
auth_service = AuthService()

# Initialize chatbot (singleton)
chatbot = None
chat_sessions = {}  # Store chat history per session


def get_chatbot():
    """Get or create chatbot instance"""
    global chatbot
    if chatbot is None:
        print("🚀 Initializing Health Chatbot...")
        chatbot = HealthChatbot()
        print("✅ Chatbot ready!")
    return chatbot


@app.route('/')
@login_required
def index():
    """Render main chat page"""
    username = session.get('username', 'User')
    role = session.get('role', 'USER')
    return render_template('index.html', username=username, role=role)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        bot = get_chatbot()
        return jsonify({
            'status': 'healthy',
            'vector_store_docs': bot.rag_chain.retriever.vector_store.index.ntotal,
            'model': bot.rag_chain.llm.model
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@app.route('/register', methods=['GET', 'POST'])
@logout_required
def register():
    """Trang đăng ký"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        success, message, user_id = auth_service.register_user(
            username, email, password, confirm_password
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@logout_required
def login():
    """Trang đăng nhập"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        success, message, user_data = auth_service.login_user(
            username, password)

        if success and user_data:
            # Lưu thông tin vào session
            session['user_id'] = user_data['id']
            session['username'] = user_data['username']
            session['email'] = user_data['email']
            session['role'] = user_data['role']

            flash(message, 'success')
            return redirect(url_for('index'))
        else:
            flash(message, 'danger')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Đăng xuất"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Tạm biệt {username}! Đã đăng xuất thành công.', 'info')
    return redirect(url_for('login'))


@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """
    Chat endpoint - Non-streaming response
    Request: {
        "message": "user question",
        "session_id": "optional session id"
    }
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Get chatbot
        bot = get_chatbot()

        # Get or create session history
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []

        history = chat_sessions[session_id]

        # Convert history format for RAGChain: [(user_msg, bot_msg), ...]
        rag_history = [(history[i]["content"], history[i+1]["content"])
                       for i in range(0, len(history)-1, 2)
                       if i+1 < len(history)]

        # Get response using RAGChain directly
        response = bot.rag_chain.ask(
            question=user_message,
            chat_history=rag_history,
            return_sources=True
        )

        # Update history
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": response})

        # Keep only last 10 turns
        if len(history) > 20:
            history = history[-20:]
            chat_sessions[session_id] = history

        # Extract sources from response if present
        sources = []
        if "📚 Nguồn:" in response:
            parts = response.split("📚 Nguồn:")
            answer_text = parts[0].strip()
            sources_text = parts[1].strip()
            sources = [s.strip() for s in sources_text.split(',') if s.strip()]
        else:
            answer_text = response

        return jsonify({
            'answer': answer_text,
            'sources': sources,
            'session_id': session_id
        })

    except Exception as e:
        print(f"❌ Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    Chat endpoint - Streaming response (SSE)
    Request: {
        "message": "user question",
        "session_id": "optional session id"
    }
    """
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id', 'default')

        if not user_message:
            return jsonify({'error': 'Message cannot be empty'}), 400

        # Get chatbot
        bot = get_chatbot()

        # Get or create session history
        if session_id not in chat_sessions:
            chat_sessions[session_id] = []

        history = chat_sessions[session_id]

        # Convert history format for RAGChain
        rag_history = [(history[i]["content"], history[i+1]["content"])
                       for i in range(0, len(history)-1, 2)
                       if i+1 < len(history)]

        def generate():
            """Generator for streaming response"""
            try:
                full_answer = ""

                # Stream response from RAGChain
                for chunk in bot.rag_chain.ask_stream(
                    question=user_message,
                    chat_history=rag_history,
                    return_sources=True
                ):
                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"

                # Update history
                history.append({"role": "user", "content": user_message})
                history.append({"role": "assistant", "content": full_answer})

                # Keep only last 10 turns
                if len(history) > 20:
                    chat_sessions[session_id] = history[-20:]

                # Extract sources from response if present
                sources = []
                if "📚 Nguồn:" in full_answer:
                    parts = full_answer.split("📚 Nguồn:")
                    sources_text = parts[1].strip()
                    sources = [s.strip()
                               for s in sources_text.split(',') if s.strip()]
                    if sources:
                        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

                # Send done signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                print(f"❌ Error in stream: {e}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        print(f"❌ Error in chat_stream endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/clear', methods=['POST'])
def clear_history():
    """Clear chat history for a session"""
    try:
        data = request.get_json()
        session_id = data.get('session_id', 'default')

        if session_id in chat_sessions:
            chat_sessions[session_id] = []

        return jsonify({'message': 'History cleared', 'session_id': session_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/<session_id>/history', methods=['GET'])
def get_history(session_id):
    """Get chat history for a session"""
    try:
        history = chat_sessions.get(session_id, [])
        return jsonify({'history': history, 'session_id': session_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 70)
    print("🏥 CHATBOT SỨC KHỎE - WEB APPLICATION")
    print("=" * 70)
    print("\n⏳ Starting Flask server...")
    print(f"🌐 Server will run at: http://localhost:5000")
    print(f"📱 Open browser and visit: http://localhost:5000")
    print("\n💡 Press Ctrl+C to stop server\n")

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
