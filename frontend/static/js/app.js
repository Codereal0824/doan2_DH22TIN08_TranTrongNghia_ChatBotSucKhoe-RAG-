// ========================================
// CHATBOT SỨC KHỎE - MAIN APPLICATION
// ========================================

class HealthChatbot {
  constructor() {
    // Để trống sessionId ban đầu, nếu chat mới sẽ gửi 'default' lên Backend
    this.sessionId = "default";
    this.isTyping = false;

    // DOM Elements
    this.welcomeScreen = document.getElementById("welcomeScreen");
    this.chatContainer = document.getElementById("chatContainer");
    this.messages = document.getElementById("messages");
    this.messageInput = document.getElementById("messageInput");
    this.sendBtn = document.getElementById("sendBtn");
    this.clearBtn = document.getElementById("clearBtn");
    this.charCount = document.getElementById("charCount");
    this.loadingOverlay = document.getElementById("loadingOverlay");

    // DOM Element cho Sidebar (Cần có thẻ ul hoặc div với id "sessionList" trong HTML)
    this.sessionList = document.getElementById("sessionList");

    this.init();
  }

  init() {
    // Event listeners
    if (this.sendBtn)
      this.sendBtn.addEventListener("click", () => this.sendMessage());
    if (this.clearBtn)
      this.clearBtn.addEventListener("click", () => this.startNewChat()); // Đổi thành startNewChat

    if (this.messageInput) {
      this.messageInput.addEventListener("input", () => {
        this.updateCharCount();
        this.autoResize();
        this.updateSendButton();
      });

      this.messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          if (!this.sendBtn.disabled) {
            this.sendMessage();
          }
        }
      });
    }

    // Example questions
    document.querySelectorAll(".example-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const question = btn.dataset.question;
        this.messageInput.value = question;
        this.updateCharCount();
        this.updateSendButton();
        this.sendMessage();
      });
    });

    // Check backend health & Load Sessions
    this.checkHealth();
    this.loadSessions(); // Gọi hàm load lịch sử ngay khi vừa mở trang
  }

  // ==========================================
  // XỬ LÝ LỊCH SỬ CHAT (SESSIONS)
  // ==========================================

  async loadSessions() {
    if (!this.sessionList) {
      console.warn(
        "⚠️ Không tìm thấy phần tử HTML có id='sessionList' để hiển thị lịch sử.",
      );
      return;
    }

    try {
      const response = await fetch("/api/user/sessions");
      const data = await response.json();

      if (response.ok && data.sessions) {
        this.sessionList.innerHTML = ""; // Xóa list cũ

        if (data.sessions.length === 0) {
          this.sessionList.innerHTML =
            '<li class="text-muted small p-2">Chưa có lịch sử chat</li>';
          return;
        }

        data.sessions.forEach((session) => {
          const li = document.createElement("li");
          // Tùy chỉnh class CSS này theo giao diện HTML của bạn
          li.className =
            "session-item p-2 mb-1 rounded cursor-pointer hover-bg-light";
          // Đổi màu nếu đang là phiên hiện tại
          if (this.sessionId == session.session_id)
            li.classList.add("bg-primary", "text-white");

          li.innerHTML = `
                    <div class="text-truncate fw-bold">${this.escapeHtml(session.session_name)}</div>
                    <div class="small opacity-75">${new Date(session.created_at).toLocaleDateString("vi-VN")}</div>
                `;

          li.addEventListener("click", () =>
            this.loadChatHistory(session.session_id),
          );
          this.sessionList.appendChild(li);
        });
      }
    } catch (error) {
      console.error("❌ Lỗi load sessions:", error);
    }
  }

  async loadChatHistory(sessionId) {
    this.sessionId = sessionId; // Cập nhật ID hiện tại

    // Clear màn hình hiện tại
    if (this.messages) this.messages.innerHTML = "";
    if (this.welcomeScreen) this.welcomeScreen.classList.add("hidden");
    if (this.chatContainer) this.chatContainer.classList.add("active");
    if (this.loadingOverlay) this.loadingOverlay.classList.add("active");

    try {
      const response = await fetch(`/api/sessions/${sessionId}/history`);
      const data = await response.json();

      if (response.ok && data.history) {
        // Render lại từng tin nhắn
        data.history.forEach((msg) => {
          if (msg.role === "user") {
            this.addMessage(msg.content, "user");
          } else {
            const messageEl = this.createBotMessage("");
            const contentEl = messageEl.querySelector(".message-content");
            contentEl.innerHTML = this.formatText(msg.content);
          }
        });
        this.scrollToBottom();
      }

      // Highlight lại cái Sidebar
      this.loadSessions();
    } catch (error) {
      console.error("❌ Lỗi load chat history:", error);
      this.showError("Không thể tải lịch sử đoạn chat này.");
    } finally {
      if (this.loadingOverlay) this.loadingOverlay.classList.remove("active");
    }
  }

  startNewChat() {
    // Đặt lại session ID về default để Backend tự tạo mới
    this.sessionId = "default";
    if (this.messages) this.messages.innerHTML = "";
    if (this.chatContainer) this.chatContainer.classList.remove("active");
    if (this.welcomeScreen) this.welcomeScreen.classList.remove("hidden");
    this.loadSessions(); // Bỏ highlight bên sidebar
  }

  // ==========================================
  // XỬ LÝ GIAO DIỆN & STREAMING
  // ==========================================

  updateCharCount() {
    if (!this.charCount || !this.messageInput) return;
    const length = this.messageInput.value.length;
    this.charCount.textContent = `${length} / 2000`;
  }

  autoResize() {
    if (!this.messageInput) return;
    this.messageInput.style.height = "auto";
    this.messageInput.style.height = this.messageInput.scrollHeight + "px";
  }

  updateSendButton() {
    if (!this.sendBtn || !this.messageInput) return;
    const message = this.messageInput.value.trim();
    this.sendBtn.disabled = !message || this.isTyping;
  }

  async checkHealth() {
    if (this.loadingOverlay) this.loadingOverlay.classList.add("active");

    try {
      const response = await fetch("/api/health");
      const data = await response.json();

      if (data.status === "healthy") {
        console.log("✅ Backend ready:", data);
        setTimeout(() => {
          if (this.loadingOverlay)
            this.loadingOverlay.classList.remove("active");
        }, 500);
      } else {
        throw new Error("Backend not healthy");
      }
    } catch (error) {
      console.error("❌ Backend error:", error);
      this.showError("Không thể kết nối với server. Vui lòng thử lại sau.");
      if (this.loadingOverlay) this.loadingOverlay.classList.remove("active");
    }
  }

  async sendMessage() {
    const message = this.messageInput.value.trim();
    if (!message || this.isTyping) return;

    if (this.welcomeScreen) this.welcomeScreen.classList.add("hidden");
    if (this.chatContainer) this.chatContainer.classList.add("active");

    this.addMessage(message, "user");

    this.messageInput.value = "";
    this.messageInput.style.height = "auto";
    this.updateCharCount();
    this.updateSendButton();

    this.isTyping = true;
    this.updateSendButton();
    const typingId = this.addTypingIndicator();

    try {
      await this.streamResponse(message, typingId);
    } catch (error) {
      console.error("❌ Error:", error);
      this.removeTypingIndicator(typingId);
      this.addMessage(
        "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại.",
        "bot",
        true,
      );
    } finally {
      this.isTyping = false;
      this.updateSendButton();
      this.messageInput.focus();
    }
  }

  async streamResponse(message, typingId) {
    try {
      console.log("📤 Sending message:", message);

      const response = await fetch("/api/chat/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: message,
          session_id: this.sessionId,
        }),
      });

      console.log("📥 Response status:", response.status);

      if (!response.ok) {
        throw new Error(`Network response was not ok: ${response.status}`);
      }

      this.removeTypingIndicator(typingId);

      const messageEl = this.createBotMessage("");
      const contentEl = messageEl.querySelector(".message-content");
      let fullAnswer = "";
      let sources = [];

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));

              // --- HỨNG SESSION ID TỪ BACKEND ĐỂ GÁN VÀO BIẾN ---
              if (data.type === "session_id") {
                this.sessionId = data.session_id;
                this.loadSessions(); // Load lại Sidebar để hiện Chat mới
              } else if (data.type === "token") {
                fullAnswer += data.content;
                contentEl.innerHTML = this.formatText(fullAnswer);
                this.scrollToBottom();
              } else if (data.type === "sources") {
                sources = data.sources;
              } else if (data.type === "done") {
                console.log("✅ Stream done");
                if (sources && sources.length > 0) {
                  this.addSources(messageEl, sources);
                }
              } else if (data.type === "error") {
                throw new Error(data.error);
              }
            } catch (e) {
              console.warn("JSON parse error in stream:", e, "Line:", line);
            }
          }
        }
      }
    } catch (error) {
      console.error("❌ Stream error:", error);
      throw error;
    }
  }

  addMessage(content, type, isError = false) {
    if (!this.messages) return null;
    const messageDiv = document.createElement("div");
    messageDiv.className = `message message-${type} clearfix`;

    if (type === "user") {
      messageDiv.innerHTML = `
                <div class="message-content">
                    ${this.escapeHtml(content)}
                </div>
            `;
    } else {
      messageDiv.innerHTML = `
                <div class="message-avatar">🏥</div>
                <div class="message-body">
                    <div class="message-content ${isError ? "error" : ""}">
                        ${isError ? content : this.formatText(content)}
                    </div>
                </div>
            `;
    }

    this.messages.appendChild(messageDiv);
    this.scrollToBottom();

    return messageDiv;
  }

  createBotMessage(content) {
    if (!this.messages) return document.createElement("div");
    const messageDiv = document.createElement("div");
    messageDiv.className = "message message-bot clearfix";
    messageDiv.innerHTML = `
            <div class="message-avatar">🏥</div>
            <div class="message-body">
                <div class="message-content">${content}</div>
            </div>
        `;
    this.messages.appendChild(messageDiv);
    this.scrollToBottom();
    return messageDiv;
  }

  addSources(messageEl, sources) {
    if (!sources || sources.length === 0) return;

    const messageBody = messageEl.querySelector(".message-body");
    if (!messageBody || messageBody.querySelector(".message-sources")) return;

    const sourcesDiv = document.createElement("div");
    sourcesDiv.className = "message-sources";

    const uniqueSources = [...new Set(sources)];

    sourcesDiv.innerHTML = `
            <strong>📚 Nguồn tham khảo:</strong>
            ${uniqueSources
              .map(
                (source) =>
                  `<span class="source-item">${this.escapeHtml(source)}</span>`,
              )
              .join("")}
        `;

    messageBody.appendChild(sourcesDiv);
    this.scrollToBottom();
  }

  addTypingIndicator() {
    if (!this.messages) return null;
    const id = "typing_" + Date.now();
    const messageDiv = document.createElement("div");
    messageDiv.id = id;
    messageDiv.className = "message message-bot clearfix";
    messageDiv.innerHTML = `
            <div class="message-avatar">🏥</div>
            <div class="message-body">
                <div class="message-content">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
    this.messages.appendChild(messageDiv);
    this.scrollToBottom();
    return id;
  }

  removeTypingIndicator(id) {
    if (!id) return;
    const indicator = document.getElementById(id);
    if (indicator) {
      indicator.remove();
    }
  }

  scrollToBottom() {
    setTimeout(() => {
      if (this.chatContainer) {
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
      }
    }, 100);
  }

  formatText(text) {
    if (!text) return "";
    text = this.escapeHtml(text);
    text = text.replace(/\*\*(.*?)\*\*/g, "<b>$1</b>");
    text = text.replace(/\n/g, "<br>");
    text = text.replace(/<br>- /g, "<br>• ");
    return text;
  }

  escapeHtml(text) {
    if (!text) return "";
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  showError(message) {
    this.addMessage(message, "bot", true);
  }
}

// Initialize app when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  window.chatbot = new HealthChatbot();
});
