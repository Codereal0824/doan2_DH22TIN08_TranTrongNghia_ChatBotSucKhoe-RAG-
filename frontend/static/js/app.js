// ========================================
// CHATBOT SỨC KHỎE - MAIN APPLICATION
// ========================================

class HealthChatbot {
  constructor() {
    this.sessionId = this.generateSessionId();
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

    this.init();
  }

  init() {
    // Event listeners
    this.sendBtn.addEventListener("click", () => this.sendMessage());
    this.clearBtn.addEventListener("click", () => this.clearChat());

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

    // Check backend health
    this.checkHealth();
  }

  generateSessionId() {
    return (
      "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9)
    );
  }

  updateCharCount() {
    const length = this.messageInput.value.length;
    this.charCount.textContent = `${length} / 2000`;
  }

  autoResize() {
    this.messageInput.style.height = "auto";
    this.messageInput.style.height = this.messageInput.scrollHeight + "px";
  }

  updateSendButton() {
    const message = this.messageInput.value.trim();
    this.sendBtn.disabled = !message || this.isTyping;
  }

  async checkHealth() {
    this.loadingOverlay.classList.add("active");

    try {
      const response = await fetch("/api/health");
      const data = await response.json();

      if (data.status === "healthy") {
        console.log("✅ Backend ready:", data);
        setTimeout(() => {
          this.loadingOverlay.classList.remove("active");
        }, 500);
      } else {
        throw new Error("Backend not healthy");
      }
    } catch (error) {
      console.error("❌ Backend error:", error);
      this.showError("Không thể kết nối với server. Vui lòng thử lại sau.");
      this.loadingOverlay.classList.remove("active");
    }
  }

  async sendMessage() {
    const message = this.messageInput.value.trim();
    if (!message || this.isTyping) return;

    // Hide welcome, show chat
    this.welcomeScreen.classList.add("hidden");
    this.chatContainer.classList.add("active");

    // Add user message
    this.addMessage(message, "user");

    // Clear input
    this.messageInput.value = "";
    this.updateCharCount();
    this.autoResize();
    this.updateSendButton();

    // Set typing state
    this.isTyping = true;
    const typingId = this.addTypingIndicator();

    try {
      // Call streaming API
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
    }
  }

  async streamResponse(message, typingId) {
    try {
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

      if (!response.ok) {
        throw new Error("Network response was not ok");
      }

      // Remove typing indicator
      this.removeTypingIndicator(typingId);

      // Create bot message element
      const messageEl = this.createBotMessage("");
      const contentEl = messageEl.querySelector(".message-content");
      let fullAnswer = "";
      let sources = [];

      // Read stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));

            if (data.type === "token") {
              fullAnswer += data.content;
              contentEl.textContent = fullAnswer;
              this.scrollToBottom();
            } else if (data.type === "sources") {
              sources = data.sources;
            } else if (data.type === "done") {
              // Add sources if available
              if (sources && sources.length > 0) {
                this.addSources(messageEl, sources);
              }
            } else if (data.type === "error") {
              throw new Error(data.error);
            }
          }
        }
      }
    } catch (error) {
      console.error("Stream error:", error);
      throw error;
    }
  }

  addMessage(content, type, isError = false) {
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
    const indicator = document.getElementById(id);
    if (indicator) {
      indicator.remove();
    }
  }

  async clearChat() {
    if (!confirm("Bạn có chắc muốn xóa lịch sử chat?")) return;

    try {
      await fetch("/api/clear", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: this.sessionId,
        }),
      });

      // Clear UI
      this.messages.innerHTML = "";
      this.chatContainer.classList.remove("active");
      this.welcomeScreen.classList.remove("hidden");

      console.log("✅ Chat history cleared");
    } catch (error) {
      console.error("❌ Clear error:", error);
      this.showError("Không thể xóa lịch sử. Vui lòng thử lại.");
    }
  }

  scrollToBottom() {
    setTimeout(() => {
      this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }, 100);
  }

  formatText(text) {
    // Convert newlines to <br>
    text = this.escapeHtml(text);
    text = text.replace(/\n/g, "<br>");
    return text;
  }

  escapeHtml(text) {
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
  const chatbot = new HealthChatbot();
  window.chatbot = chatbot; // For debugging
});
