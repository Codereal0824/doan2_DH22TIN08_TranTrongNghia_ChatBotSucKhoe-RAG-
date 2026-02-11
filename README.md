HƯỚNG DẪN CHẠY CHATBOT TƯ VẤN SỨC KHỎE AI (RAG)

⚠️ Áp dụng cho Windows + Python 3.10
⚠️ Đã kiểm chứng theo quá trình debug thực tế

1️⃣ YÊU CẦU HỆ THỐNG

Python: 3.10.x (khuyến nghị 3.10.11)

Hệ điều hành: Windows 10/11 64-bit

RAM: ≥ 8GB

Internet: để tải thư viện & gọi Groq API

2️⃣ CLONE PROJECT
git clone https://github.com/yourusername/Chatbot_suckhoe.git
cd Chatbot_suckhoe

3️⃣ TẠO & KÍCH HOẠT MÔI TRƯỜNG ẢO (BẮT BUỘC)
python -m venv venv
venv\Scripts\activate

Kiểm tra đúng môi trường:

where python

👉 Phải ra đường dẫn dạng:

...Chatbot_suckhoe\venv\Scripts\python.exe

4️⃣ CÀI ĐẶT TOÀN BỘ THƯ VIỆN (THEO ĐÚNG THỨ TỰ)

LUÔN dùng python -m pip install để tránh lỗi sai môi trường

🔹 4.1 Nâng cấp pip
python -m pip install --upgrade pip

🔹 4.2 Cài các thư viện cốt lõi
python -m pip install flask flask-cors python-dotenv

🔹 4.3 Cài LLM & RAG stack
python -m pip install groq
python -m pip install sentence-transformers
python -m pip install faiss-cpu

🔹 4.4 Cài LangChain
python -m pip install langchain langchain-community

🔹 4.5 (Nếu dùng tài liệu PDF / Word)
python -m pip install pypdf python-docx

5️⃣ TẠO FILE requirements.txt (RẤT QUAN TRỌNG)

Sau khi cài xong hết:

pip freeze > requirements.txt

6️⃣ CẤU HÌNH BIẾN MÔI TRƯỜNG
🔹 6.1 Tạo file .env
copy config\.env.example config\.env

🔹 6.2 Nội dung file .env

# Groq API

GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# (Nếu dùng SQL Server)

SQL_SERVER=localhost
SQL_DATABASE=HealthChatbotDB
SQL_USERNAME=sa
SQL_PASSWORD=YourStrongPassword123!
SQL_PORT=1433

⚠️ Không push file .env lên GitHub

7️⃣ CHUẨN BỊ DỮ LIỆU
🔹 7.1 Tài liệu y tế (RAG)

Copy PDF / DOCX vào:

data/health_knowledge/

Ví dụ:

data/health_knowledge/
├── health_guide.pdf
├── common_diseases.pdf
└── prevention.docx

🔹 7.2 Vector store

Thư mục sẽ được tạo tự động:

data/vector_store/

8️⃣ CHẠY ỨNG DỤNG (CHUẨN NHẤT)
✅ Cách 1 – Khuyến nghị
python run.py

Nếu thành công sẽ thấy:

- Running on http://127.0.0.1:5000

Mở trình duyệt:

http://localhost:5000

⚠️ Cách 2 – Nếu lỗi import (ít gặp)
set PYTHONPATH=d:\NAM4_HOC_KY2\Chatbot_suckhoe
python frontend/app.py

9️⃣ KIỂM TRA NHANH HỆ THỐNG
🔹 Test Groq
from groq import Groq

🔹 Test Embedding
from sentence_transformers import SentenceTransformer

🔹 Test FAISS
import faiss

Không lỗi → hệ thống OK ✅

10️⃣ CÁC LỖI THƯỜNG GẶP & CÁCH SỬA
Lỗi Cách xử lý
No module named 'dotenv' pip install python-dotenv
No module named 'groq' pip install groq
No module named 'sentence_transformers' pip install sentence-transformers
No module named 'faiss' pip install faiss-cpu
No module named 'flask' pip install flask
No module named 'flask_cors' pip install flask-cors
GROQ_API_KEY not found Kiểm tra file .env
11️⃣ GHI CHÚ QUAN TRỌNG CHO ĐỒ ÁN

Chatbot không chẩn đoán bệnh

Không kê đơn thuốc

Chỉ cung cấp thông tin tham khảo

Có disclaimer rõ ràng → đúng chuẩn đạo đức AI
