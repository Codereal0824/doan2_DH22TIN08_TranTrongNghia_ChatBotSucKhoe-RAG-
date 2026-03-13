# RAG HEALTH CHATBOT - COMPLETE PROJECT SNAPSHOT

**Audit Date:** 2025-01-26  
**Auditor:** Senior AI Engineer  
**Purpose:** Comprehensive Technical Documentation for Stakeholder Review

---

## SECTION 1: PROJECT INFORMATION

### Basic Information

- **Project Name:** Chatbot Tư Vấn Sức Khỏe (Health Advisory Chatbot)
- **Purpose:** Educational health information system using Retrieval-Augmented Generation (RAG) for accurate, grounded medical knowledge delivery in Vietnamese
- **Type:** Web Application with RAG Pipeline
- **Primary Language:** Python 3.9+
- **Secondary Languages:** JavaScript (ES6), HTML5, CSS3

### Technology Stack

**Backend Framework:**

- Flask 3.0.0 (Web Server)
- LangChain 0.2.0+ (RAG Orchestration)
- langchain-groq (LLM Integration)

**LLM & Embeddings:**

- **LLM Provider:** Groq Cloud API
- **LLM Model:** llama-3.3-70b-versatile
- **Embedding Model:** sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- **Embedding Dimension:** 384

**Vector Database:**

- FAISS-CPU 1.7.4+ (IndexFlatL2 - Exact L2 Distance Search)
- Storage: Persistent index + metadata (pickle)

**Document Processing:**

- PyPDF (PDF extraction)
- python-docx (Word documents)
- unstructured (Multi-format support)
- Custom section-based chunker

**Database:**

- SQL Server (User Management via pyodbc + sqlalchemy)
- SQLite (Alternative/Development)

**Authentication:**

- JWT-based sessions (werkzeug.security)
- Flask session management
- Role-based access control (USER, ADMIN)

**Frontend:**

- HTML5/CSS3/Vanilla JavaScript
- Server-Sent Events (SSE) for streaming responses
- Responsive UI (Gemini-inspired design)

### Configuration Parameters

```python
# RAG Configuration
TOP_K_RETRIEVAL = 2              # Number of documents retrieved
CHUNK_SIZE = 1000                # Characters per chunk (fallback)
CHUNK_OVERLAP = 100              # Overlap between chunks
CHUNKING_METHOD = "section-based" # Primary strategy

# LLM Configuration
MODEL = "llama-3.3-70b-versatile"
TEMPERATURE = 0.0                # Strict mode (no creativity)
MAX_TOKENS = 512                 # Short, focused responses

# Thresholds
RELEVANCE_THRESHOLD_L2 = 150.0   # L2 distance cutoff (Vietnamese)
SEMANTIC_THRESHOLD = 0.25        # Minimum semantic similarity
KEYWORD_BOOST_FACTOR = 0.60      # Disease keyword boost (40%)
PRIMARY_MATCH_BOOST = 0.40       # Primary topic match (60%)

# Rate Limiting
DEFAULT_RATE_LIMIT = "100 per hour"
LOGIN_RATE_LIMIT = "5 per minute"
REGISTER_RATE_LIMIT = "3 per minute"
CHAT_RATE_LIMIT = "20 per minute"
```

### Key Features

1. **Strict RAG Mode:** TEMPERATURE=0.0 prevents hallucination, enforces document grounding
2. **Section-Based Chunking:** Preserves medical document structure (8 standard sections)
3. **Multi-Level Filtering:**
   - L2 distance threshold (150.0)
   - Semantic similarity (0.25)
   - Policy-based content filtering
4. **Keyword Boosting:** Improved topical relevance for disease-specific queries
5. **Vietnamese Optimization:** Multilingual embeddings + accent normalization
6. **Safety Controls:** Query blocking + post-generation sanitization
7. **Streaming Responses:** Real-time token-by-token generation via SSE
8. **Authentication:** Secure user management with rate limiting

### Project Statistics

- **Total Python Files:** 33
- **Total Documents:** 45 health knowledge files
- **Vector Store Size:** ~45 documents (post chunking: ~200-300 chunks)
- **Test Questions:** 440 comprehensive test cases
- **Supported Formats:** .txt, .md, .pdf, .docx

---

## SECTION 2: DIRECTORY TREE

```
Chatbot_suckhoe/
├── run.py                           # Application entry point
├── requirements.txt                 # Python dependencies
├── rebuild_vector_database.py       # Rebuild FAISS index script
├── rebuild_database.bat            # Windows batch script for DB rebuild
├── start_chatbot.bat               # Windows startup script
├── test_refactor.py                # Refactoring tests
├── test_chat_questions.txt         # 440 test questions (24 topics)
│
├── config/                         # Configuration Management
│   ├── __init__.py
│   └── config.py                   # Centralized config (env-based)
│
├── backend/                        # Core Backend Logic
│   ├── __init__.py
│   │
│   ├── api/                        # External API Integration
│   │   ├── __init__.py
│   │   └── groq_client.py          # Groq LLM client (retry + rate limiting)
│   │
│   ├── auth/                       # Authentication & Authorization
│   │   ├── __init__.py
│   │   ├── auth_service.py         # User registration/login/password mgmt
│   │   └── decorators.py           # Auth decorators (@login_required)
│   │
│   ├── database/                   # Data Persistence Layer
│   │   ├── __init__.py
│   │   ├── vector_store.py         # FAISS index management
│   │   └── sql_handler.py          # SQL Server/SQLite handler
│   │
│   ├── rag/                        # RAG Pipeline Core
│   │   ├── __init__.py
│   │   ├── embeddings.py           # Sentence-BERT embeddings (caching)
│   │   ├── retriever.py            # Retrieval with keyword boosting
│   │   ├── prompts.py              # System prompts & templates
│   │   └── chain.py                # RAG orchestration (retrieve + generate)
│   │
│   └── utils/                      # Utility Modules
│       ├── __init__.py
│       ├── chunking.py             # Section-based + token-based chunking
│       ├── document_loader.py      # Multi-format document loader
│       ├── query_normalizer.py     # Query blocking & normalization
│       ├── logger.py               # Centralized logging
│       ├── prompts.py              # Additional prompts (legacy)
│       └── prompts_backup.py       # Prompt version control
│
├── frontend/                       # Web Interface
│   ├── app.py                      # Flask routes (login, chat, streaming)
│   ├── templates/                  # HTML Templates
│   │   ├── index.html              # Main chat interface
│   │   ├── login.html              # Login page
│   │   └── register.html           # Registration page
│   └── static/                     # Static Assets
│       ├── css/
│       │   └── style.css           # Gemini-inspired responsive design
│       └── js/
│           └── app.js              # Chat client (SSE streaming, auth)
│
├── data/                           # Knowledge Base & Vector Store
│   ├── health_knowledge/           # 45 Medical Documents
│   │   ├── beo_phi_do_loi_song.txt
│   │   ├── benh_tim_mach.txt
│   │   ├── buong_trung_da_nang.txt
│   │   ├── camlanh_cacum.txt
│   │   ├── covid19.txt
│   │   ├── cum_mua.txt
│   │   ├── dai_thao_duong.txt
│   │   ├── dau_lung.txt
│   │   ├── gout.txt
│   │   ├── hen_phe_quan.txt
│   │   ├── ho_thong_thuong.txt
│   │   ├── lanh_tinh_duc.txt
│   │   ├── luoi_van_dong.txt
│   │   ├── mat_ngu.txt
│   │   ├── mat_nuoc.txt
│   │   ├── roi_loan_tieu_hoa.txt
│   │   ├── say_nang.txt
│   │   ├── soi_than.txt
│   │   ├── stress.txt
│   │   ├── suy_dinh_duong.txt
│   │   ├── tang_huyet_ap.txt
│   │   ├── tao_bon_chuc_nang.txt
│   │   ├── tiem_chung.txt
│   │   ├── tram_cam.txt
│   │   ├── ung_thu.txt
│   │   ├── viem_gan_virus_b.txt
│   │   ├── viem_hong_acute.txt
│   │   ├── viem_hong_allergic.txt
│   │   ├── viem_ket_mac.txt
│   │   ├── viem_mui_di_ung.txt
│   │   ├── viem_phoi.txt
│   │   ├── viem_tai.txt
│   │   ├── viem_xoang.txt
│   │   └── [45 total files...]
│   │
│   └── vector_store/               # FAISS Persistent Storage
│       ├── health_faiss.index.faiss # FAISS IndexFlatL2
│       ├── health_faiss.index.pkl   # Document metadata
│       └── health_chatbot_index.faiss
│
├── scripts/                        # Utility Scripts
│   ├── build_vector_db.py          # Vector DB construction pipeline
│   ├── validate_content.py         # Document standardization checker
│   └── export_project.py           # Project export utility
│
├── logs/                           # Application Logs
│   └── chatbot.log                 # Timestamped logs
│
└── docs/                           # Documentation
    ├── AUTH_SETUP_GUIDE.md
    ├── CHANGELOG_V3.md
    ├── CHANGELOG_V4.1.md
    ├── COMPLETE_RAG_PIPELINE.md
    ├── CRAWL_GUIDE.md
    ├── FULL_PROJECT_CONTEXT.txt
    ├── HUONG_DAN_CRAWLER_NANG_CAP.md
    ├── HUONG_DAN_GROQ_QUOTA.md
    ├── HUONG_DAN_THEM_TAI_LIEU.md
    ├── PROJECT_STRUCTURE.md
    ├── RAG_COMPLETE_SUMMARY.md
    ├── README.md
    ├── REFACTOR_QUICK_SUMMARY.md
    ├── REFACTOR_SUMMARY.md
    ├── RETRIEVAL_FIX_SUMMARY.md
    ├── SECTION_BASED_CHUNKING.md
    ├── STRICT_RAG_IMPLEMENTATION.md
    ├── V4_SUMMARY.md
    ├── VECTOR_STORE_EXPLANATION.md
    └── VERSION_HISTORY.md
```

---

## SECTION 3: FILE METADATA TABLE

### Core Python Modules (Backend)

| File                | Path                              | Extension | Size (KB) | Modified         |
| ------------------- | --------------------------------- | --------- | --------- | ---------------- |
| run.py              | run.py                            | .py       | 0.62      | 2025-01-25 14:32 |
| config.py           | config\config.py                  | .py       | 3.84      | 2025-01-25 15:18 |
| groq_client.py      | backend\api\groq_client.py        | .py       | 6.12      | 2025-01-25 14:45 |
| auth_service.py     | backend\auth\auth_service.py      | .py       | 7.23      | 2025-01-24 10:22 |
| decorators.py       | backend\auth\decorators.py        | .py       | 1.45      | 2025-01-23 16:30 |
| vector_store.py     | backend\database\vector_store.py  | .py       | 6.78      | 2025-01-25 09:15 |
| sql_handler.py      | backend\database\sql_handler.py   | .py       | 5.91      | 2025-01-24 11:05 |
| embeddings.py       | backend\rag\embeddings.py         | .py       | 5.34      | 2025-01-25 13:20 |
| retriever.py        | backend\rag\retriever.py          | .py       | 12.45     | 2025-01-25 16:10 |
| prompts.py          | backend\rag\prompts.py            | .py       | 18.92     | 2025-01-25 15:45 |
| chain.py            | backend\rag\chain.py              | .py       | 14.67     | 2025-01-25 14:55 |
| chunking.py         | backend\utils\chunking.py         | .py       | 9.23      | 2025-01-25 12:40 |
| document_loader.py  | backend\utils\document_loader.py  | .py       | 8.56      | 2025-01-24 16:20 |
| query_normalizer.py | backend\utils\query_normalizer.py | .py       | 4.12      | 2025-01-25 10:30 |
| logger.py           | backend\utils\logger.py           | .py       | 2.34      | 2025-01-23 09:15 |

### Frontend Files

| File          | Path                             | Extension | Size (KB) | Modified         |
| ------------- | -------------------------------- | --------- | --------- | ---------------- |
| app.py        | frontend\app.py                  | .py       | 15.23     | 2025-01-25 17:05 |
| index.html    | frontend\templates\index.html    | .html     | 8.45      | 2025-01-25 11:30 |
| login.html    | frontend\templates\login.html    | .html     | 5.67      | 2025-01-24 14:20 |
| register.html | frontend\templates\register.html | .html     | 5.89      | 2025-01-24 14:25 |
| style.css     | frontend\static\css\style.css    | .css      | 12.34     | 2025-01-25 10:45 |
| app.js        | frontend\static\js\app.js        | .js       | 11.78     | 2025-01-25 16:50 |

### Scripts & Utilities

| File                       | Path                        | Extension | Size (KB) | Modified         |
| -------------------------- | --------------------------- | --------- | --------- | ---------------- |
| build_vector_db.py         | scripts\build_vector_db.py  | .py       | 7.89      | 2025-01-25 09:00 |
| validate_content.py        | scripts\validate_content.py | .py       | 4.56      | 2025-01-24 15:10 |
| export_project.py          | scripts\export_project.py   | .py       | 3.21      | 2025-01-23 12:30 |
| rebuild_vector_database.py | rebuild_vector_database.py  | .py       | 2.45      | 2025-01-24 08:45 |
| test_refactor.py           | test_refactor.py            | .py       | 5.67      | 2025-01-23 17:20 |

### Data Files (Sample)

| File                     | Path                    | Extension | Size (KB) | Modified         |
| ------------------------ | ----------------------- | --------- | --------- | ---------------- |
| test_chat_questions.txt  | test_chat_questions.txt | .txt      | 28.45     | 2025-01-26 14:10 |
| beo_phi_do_loi_song.txt  | data\health_knowledge\  | .txt      | 4.23      | 2025-01-20 10:15 |
| covid19.txt              | data\health_knowledge\  | .txt      | 6.78      | 2025-01-20 10:15 |
| dai_thao_duong.txt       | data\health_knowledge\  | .txt      | 5.12      | 2025-01-20 10:15 |
| ung_thu.txt              | data\health_knowledge\  | .txt      | 7.34      | 2025-01-20 10:15 |
| [45 total health docs]   | data\health_knowledge\  | .txt      | ~200 KB   | 2025-01-20       |
| health_faiss.index.faiss | data\vector_store\      | .faiss    | 512.34    | 2025-01-25 09:10 |
| health_faiss.index.pkl   | data\vector_store\      | .pkl      | 145.67    | 2025-01-25 09:10 |

### Configuration & Documentation

| File                     | Path                     | Extension | Size (KB) | Modified         |
| ------------------------ | ------------------------ | --------- | --------- | ---------------- |
| requirements.txt         | requirements.txt         | .txt      | 1.89      | 2025-01-25 08:30 |
| README.md                | README.md                | .md       | 8.23      | 2025-01-24 16:00 |
| PROJECT_STRUCTURE.md     | PROJECT_STRUCTURE.md     | .md       | 12.45     | 2025-01-26 12:30 |
| COMPLETE_RAG_PIPELINE.md | COMPLETE_RAG_PIPELINE.md | .md       | 15.67     | 2025-01-25 14:20 |

**Total Project Files:** ~95 files (excluding venv, cache, .git)  
**Total Size:** ~1.2 GB (including vector store + dependencies)

---

## SECTION 4: RAG ARCHITECTURE

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  (Flask Web App - HTML/CSS/JS with SSE Streaming)               │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AUTHENTICATION                              │
│  • JWT Session Management                                        │
│  • SQL Server User Database                                      │
│  • Rate Limiting (Flask-Limiter)                                 │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       RAG CHAIN (chain.py)                       │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. Query Preprocessing                                       ││
│  │    • Safety Filtering (query_normalizer.py)                 ││
│  │    • Greeting/Farewell Detection                            ││
│  │    • Keyword Extraction                                     ││
│  └─────────────────────────────────────────────────────────────┘│
│                             │                                     │
│                             ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 2. RETRIEVAL (retriever.py)                                 ││
│  │    ┌────────────────────────────────────────┐               ││
│  │    │ Query Embedding (embeddings.py)        │               ││
│  │    │ • Model: paraphrase-multilingual       │               ││
│  │    │   -MiniLM-L12-v2 (384-dim)             │               ││
│  │    │ • LRU caching for performance          │               ││
│  │    └────────────┬───────────────────────────┘               ││
│  │                 │                                            ││
│  │                 ▼                                            ││
│  │    ┌────────────────────────────────────────┐               ││
│  │    │ Vector Search (vector_store.py)        │               ││
│  │    │ • FAISS IndexFlatL2 (exact search)     │               ││
│  │    │ • L2 distance computation              │               ││
│  │    │ • Top-K retrieval (K=2)                │               ││
│  │    └────────────┬───────────────────────────┘               ││
│  │                 │                                            ││
│  │                 ▼                                            ││
│  │    ┌────────────────────────────────────────┐               ││
│  │    │ Keyword Boosting                       │               ││
│  │    │ • Disease keyword detection            │               ││
│  │    │ • Primary match (60% boost)            │               ││
│  │    │ • Secondary match (40% boost)          │               ││
│  │    │ • Accent normalization                 │               ││
│  │    └────────────┬───────────────────────────┘               ││
│  │                 │                                            ││
│  │                 ▼                                            ││
│  │    ┌────────────────────────────────────────┐               ││
│  │    │ Score Filtering                        │               ││
│  │    │ • L2 distance < 150.0                  │               ││
│  │    │ • Semantic similarity > 0.25           │               ││
│  │    │ • Fallback if no docs pass             │               ││
│  │    └────────────┬───────────────────────────┘               ││
│  │                 │                                            ││
│  │                 ▼                                            ││
│  │    [Retrieved Documents with Metadata]                      ││
│  └─────────────────────────────────────────────────────────────┘│
│                             │                                     │
│                             ▼                                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 3. GENERATION (groq_client.py)                              ││
│  │    ┌────────────────────────────────────────┐               ││
│  │    │ Context Formatting (prompts.py)        │               ││
│  │    │ • Format retrieved docs                │               ││
│  │    │ • Build message array                  │               ││
│  │    │ • System prompt injection              │               ││
│  │    └────────────┬───────────────────────────┘               ││
│  │                 │                                            ││
│  │                 ▼                                            ││
│  │    ┌────────────────────────────────────────┐               ││
│  │    │ LLM Call (Groq API)                    │               ││
│  │    │ • Model: llama-3.3-70b-versatile       │               ││
│  │    │ • Temperature: 0.0 (strict)            │               ││
│  │    │ • Max tokens: 512                      │               ││
│  │    │ • Streaming: SSE chunks                │               ││
│  │    │ • Retry logic (rate limits)            │               ││
│  │    └────────────┬───────────────────────────┘               ││
│  │                 │                                            ││
│  │                 ▼                                            ││
│  │    ┌────────────────────────────────────────┐               ││
│  │    │ Post-Generation Sanitization           │               ││
│  │    │ • Policy violation check               │               ││
│  │    │ • Diagnosis detection                  │               ││
│  │    │ • Prescription blocking                │               ││
│  │    │ • Fallback response if violated        │               ││
│  │    └────────────┬───────────────────────────┘               ││
│  │                 │                                            ││
│  │                 ▼                                            ││
│  │    [Safe, Grounded Response + Sources]                      ││
│  └─────────────────────────────────────────────────────────────┘│
└────────────────────┬───────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    RESPONSE STREAMING                            │
│  • Server-Sent Events (SSE)                                      │
│  • Token-by-token delivery                                       │
│  • Source attribution                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. Document Loader (`backend/utils/document_loader.py`)

**Purpose:** Ingest multi-format documents into RAG pipeline

**Supported Formats:**

- `.txt` - Plain text (UTF-8)
- `.md` - Markdown
- `.pdf` - PDF extraction via PyPDF
- `.docx` - Word documents via python-docx

**Key Functions:**

- `load_file(file_path)` - Auto-detect format and load
- `load_directory(directory, recursive=True)` - Batch loading
- `load_pdf/docx/text()` - Format-specific loaders

**Output:** `{'content': str, 'metadata': {'source', 'type', 'pages', ...}}`

#### 2. Chunking Strategy (`backend/utils/chunking.py`)

**Primary Method:** Section-Based Chunking

**Standard 8-Section Format:**

```
1. Tổng quan (Overview)
2. Dấu hiệu nhận biết (Symptoms)
3. Nguyên nhân (Causes)
4. Ảnh hưởng đến sức khỏe (Health Impact)
5. Chăm sóc & hỗ trợ tại nhà (Home Care)
6. Phòng ngừa (Prevention)
7. Khi nào cần đi khám (When to See Doctor)
8. Lưu ý quan trọng (Important Notes)
```

**Algorithm:**

1. Parse document for section headers (`\d+\.\s+Title`)
2. Extract title + content for each section
3. Create self-contained chunks: `{doc_title} - {section_title}:\n\n{content}`
4. Preserve semantic meaning within medical context

**Fallback:** Token-based chunking (RecursiveCharacterTextSplitter)

- Chunk size: 1000 characters
- Overlap: 100 characters
- Separators: `\n\n`, `\n`, `. `, `, `, etc.

**Metadata per Chunk:**

- `chunk_index`, `total_chunks`
- `section_number`, `section_title`
- `document_title`, `source`
- `chunking_method` (section-based | token-based)

#### 3. Embeddings (`backend/rag/embeddings.py`)

**Model:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

**Specifications:**

- Dimension: 384
- Languages: 50+ (optimized for Vietnamese)
- Max sequence length: 128 tokens
- Framework: PyTorch + sentence-transformers

**Features:**

- **LRU Caching:** `@lru_cache(maxsize=1000)` for repeated queries
- **Batch Encoding:** `encode_batch()` for efficient document processing
- **Similarity:** Cosine similarity computation

**Methods:**

- `encode_text(text)` - Single text embedding with cache
- `encode_batch(texts, batch_size=32)` - Batch processing
- `similarity(text1, text2)` - Cosine similarity score

#### 4. Vector Database (`backend/database/vector_store.py`)

**Technology:** FAISS (Facebook AI Similarity Search)

**Index Type:** `IndexFlatL2` (Exact L2 distance search)

- No approximation (accuracy critical for medical data)
- Brute-force search (manageable for 45 documents → ~300 chunks)

**Storage:**

- `health_faiss.index.faiss` - FAISS index binary
- `health_faiss.index.pkl` - Metadata (content, sources)

**Operations:**

- `add_documents(docs)` - Bulk insert embeddings
- `search(query_embedding, top_k)` - L2 distance search
- `save/load(path)` - Persistent storage

**Search Output:**

```python
{
    'content': str,
    'metadata': {'source', 'section_title', ...},
    'score': float,        # L2 distance (lower = better)
    'similarity': float,   # Converted to 0-1 scale
    'rank': int
}
```

#### 5. Retriever (`backend/rag/retriever.py`)

**Core Functionality:** Advanced document retrieval with Vietnamese optimization

**Pipeline:**

1. **Query Normalization:**
   - `normalize_query()` - Standardize medical terms
   - Accent-insensitive matching preparation

2. **Embedding Generation:**
   - Encode query with cached embedding model
   - Same 384-dim space as documents

3. **FAISS Search:**
   - Retrieve top-K candidates (K=2 default)
   - L2 distance computation

4. **Keyword Boosting (NEW):**

   ```python
   # Disease keywords: ung thư, covid, đái tháo đường, etc.
   if disease_keyword_detected:
       if primary_match:  # File is ABOUT disease
           score *= 0.40  # 60% boost
       else:              # File mentions disease
           score *= 0.60  # 40% boost
   ```

5. **Score Filtering:**
   - L2 distance threshold: 150.0 (Vietnamese-tuned)
   - Semantic similarity threshold: 0.25
   - Reject documents below thresholds

6. **Re-ranking:**
   - Sort by boosted scores
   - Return filtered + ranked results

**Key Innovation:** Accent normalization for keyword matching

```python
def remove_vietnamese_accents(text):
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
```

#### 6. Reranker

**Status:** Not implemented (current system uses keyword boosting instead)

**Reason:** With TOP_K=2 and high-quality chunking, reranking overhead not justified for current scale.

#### 7. Prompts (`backend/rag/prompts.py`)

**System Prompt Design:** Strict RAG enforcement with logical reasoning

**Key Principles:**

1. **Ground all answers in context** (no external knowledge)
2. **Allow logical inference** from documents (e.g., "is X a symptom?" → check list)
3. **Prohibit diagnosis** and prescription
4. **Short responses** (2-4 sentences)

**Prompt Components:**

- `HEALTH_CHATBOT_SYSTEM_PROMPT` - Identity and rules
- `RAG_PROMPT_TEMPLATE` - Context injection format
- `format_context(docs)` - Document formatting
- `build_messages()` - Message array construction

**Safety Filters:**

- `violates_policy(answer)` - Post-generation check
- `sanitize_answer(answer)` - Clean or reject
- Forbidden patterns: "tôi chẩn đoán", "bạn bị bệnh"

**Fallback Responses:**

- `NO_DOCS_FOUND_RESPONSE` - No relevant documents
- `STRICT_FALLBACK_RESPONSE` - Policy violation or uncertainty

(See SECTION 5 for full prompt text)

#### 8. LLM Integration (`backend/api/groq_client.py`)

**Provider:** Groq Cloud API  
**Model:** llama-3.3-70b-versatile

**Configuration:**

- Temperature: 0.0 (deterministic, no creativity)
- Max tokens: 512 (concise answers)
- Streaming: Supported via SSE

**Error Handling:**

```python
# Daily token limit (TPD) → immediate failure
if 'tokens per day' in error:
    raise Exception("API_DAILY_LIMIT")

# Short rate limits → retry with backoff
if '429' in error and wait_time < 30:
    time.sleep(wait_time)
    retry()

# Maximum 3 retries per request
```

**Methods:**

- `chat(messages, temperature, max_tokens)` - Synchronous
- `chat_stream(messages, ...)` - Generator for streaming
- `_parse_retry_after(error_msg)` - Extract wait time from error

---

## SECTION 5: ALL PROMPTS

### 1. Main System Prompt

**Location:** `backend/rag/prompts.py::HEALTH_CHATBOT_SYSTEM_PROMPT`

**Purpose:** Define chatbot identity, operational rules, and safety boundaries

```
Bạn là Chatbot Giáo dục Sức khỏe sử dụng kỹ thuật RAG (Retrieval-Augmented Generation).

NHIỆM VỤ:
Cung cấp thông tin sức khỏe phổ thông dựa trên tài liệu được truy xuất từ hệ thống.

NGUYÊN TẮC HOẠT ĐỘNG:

1. NỀN TẢNG - CHỈ SỬ DỤNG TÀI LIỆU:
   • Mọi câu trả lời PHẢI dựa trên nội dung trong CONTEXT
   • KHÔNG được sử dụng kiến thức y học bên ngoài tài liệu
   • KHÔNG được thêm thông tin từ training data

2. SUY LUẬN LOGIC - ĐƯỢC PHÉP:
   ✔ Tổng hợp thông tin từ nhiều đoạn trong tài liệu
   ✔ Liên kết các ý có trong tài liệu
   ✔ Diễn đạt lại và giải thích nội dung tài liệu
   ✔ So sánh thông tin từ nhiều tài liệu
   ✔ Trích xuất thông tin để trả lời câu hỏi cụ thể

   Ví dụ ĐƯỢC PHÉP:
   - Tài liệu viết: "Triệu chứng: đau đầu, sốt, ho"
   - Hỏi: "Đau đầu có phải triệu chứng không?"
   - ✅ Trả lời: "Có, đau đầu là một trong các triệu chứng"

3. CẤM TUYỆT ĐỐI:
   ✘ Thêm kiến thức y học không có trong tài liệu
   ✘ Đưa ra thông tin dựa trên kinh nghiệm chung
   ✘ Chẩn đoán bệnh cho người dùng
   ✘ Kê đơn thuốc hoặc phác đồ điều trị cá nhân

4. XỬ LÝ CÁC LOẠI CÂU HỎI:

   a) Câu hỏi triệu chứng:
      "Triệu chứng của X là gì?"
      → Liệt kê tất cả triệu chứng có trong tài liệu X

   b) Câu hỏi kiểm tra:
      "A có phải triệu chứng của B không?"
      → Kiểm tra tài liệu B có liệt kê A không

   c) Câu hỏi tìm kiếm ngược:
      "Triệu chứng X có thể là dấu hiệu của bệnh gì?"
      → Tìm tất cả bệnh có triệu chứng X trong tài liệu

   d) Câu hỏi ghép:
      "Đau đầu và chóng mặt là dấu hiệu của bệnh gì?"
      → Tìm bệnh có CẢ HAI triệu chứng này

   e) Câu hỏi so sánh:
      "X và Y khác nhau như thế nào?"
      → So sánh thông tin từ 2 tài liệu

5. QUY TẮC QUAN TRỌNG:
   • Nếu tài liệu CÓ thông tin → Suy luận logic và trả lời
   • Nếu tài liệu KHÔNG CÓ → Từ chối: "Hiện tài liệu chưa cung cấp thông tin về nội dung này. Bạn nên tham khảo nhân viên y tế để được tư vấn."
   • Khi không chắc chắn → Ưu tiên TỪ CHỐI thay vì đoán

PHONG CÁCH VIẾT:
• Ngắn gọn: 2-4 câu, đi thẳng vào vấn đề
• Tự nhiên: Viết dễ hiểu, không học thuật
• Chính xác: Mọi thông tin đều có căn cứ trong tài liệu
```

**Variables:** None (static system-level instruction)

**Safety Rules:**

1. Document grounding mandatory
2. No external medical knowledge
3. No diagnosis or prescription
4. Logical inference permitted (within documents)
5. Fallback on uncertainty

---

### 2. RAG Prompt Template

**Location:** `backend/rag/prompts.py::RAG_PROMPT_TEMPLATE`

**Purpose:** Structure user query + retrieved context for LLM with detailed reasoning instructions

```
Câu hỏi: {question}

Thông tin từ tài liệu:
{context}

==================================================
HƯỚNG DẪN TRẢ LỜI
==================================================

BƯỚC 1: PHÂN TÍCH CÂU HỎI
- Đọc kỹ câu hỏi: Người dùng hỏi về VẤN ĐỀ GÌ?
- Xác định loại câu hỏi:
  * Hỏi triệu chứng: "Triệu chứng của X là gì?"
  * Hỏi kiểm tra: "A có phải triệu chứng của B không?"
  * Hỏi tìm kiếm: "Triệu chứng X là dấu hiệu của bệnh gì?"
  * Hỏi ghép: "A và B có phải dấu hiệu của bệnh gì?"
  * Hỏi so sánh: "X và Y khác nhau như thế nào?"
  * Hỏi mối liên hệ: "X có liên quan đến Y không?"

BƯỚC 2: TÌM THÔNG TIN TRONG TÀI LIỆU
- Đọc kỹ từng dòng trong phần "Thông tin từ tài liệu"
- Tìm thông tin TRỰC TIẾP trả lời câu hỏi
- Chú ý: TẤT CẢ thông tin cần thiết phải CÓ TRONG tài liệu

BƯỚC 3: SUY LUẬN LOGIC (CHO PHÉP)

✅ ĐƯỢC PHÉP - Các phép suy luận hợp lệ:

1. Tổng hợp và liệt kê:
   - Tài liệu: "Triệu chứng: A, B, C"
   - Hỏi: "Triệu chứng là gì?" → Liệt kê A, B, C ✅

2. Kiểm tra trong danh sách:
   - Tài liệu: "Triệu chứng: đau đầu, sốt, ho"
   - Hỏi: "Đau đầu có phải triệu chứng không?" → "Có" ✅

3. Tìm kiếm ngược (reverse lookup):
   - Tài liệu A: "Bệnh X có triệu chứng: đau đầu"
   - Tài liệu B: "Bệnh Y có triệu chứng: đau đầu, sốt"
   - Hỏi: "Đau đầu là triệu chứng của bệnh gì?" → "X và Y" ✅

4. So sánh nhiều tài liệu:
   - Tài liệu X: [nội dung về X]
   - Tài liệu Y: [nội dung về Y]
   - Hỏi: "X và Y khác gì nhau?" → So sánh các điểm ✅

5. Kiểm tra mối liên hệ:
   - Tài liệu X: "Nguyên nhân: Y..."
   - Hỏi: "X và Y có liên quan không?" → "Y là nguyên nhân của X" ✅

❌ KHÔNG ĐƯỢC - Các hành vi cấm:

1. Thêm kiến thức bên ngoài:
   - ❌ "Bệnh này thường gặp ở người lớn tuổi" (nếu tài liệu không nói)
   - ❌ "Nên uống nhiều nước" (nếu tài liệu không khuyến cáo)

2. Suy diễn không có căn cứ:
   - ❌ "Bệnh A có triệu chứng X, bệnh B cũng vậy, nên chúng có liên quan"
   - ✅ "Tài liệu không đề cập mối liên hệ giữa A và B"

3. Trả lời lạc đề:
   - Hỏi về "đau lưng" → ❌ Không được nói về "đau khớp gối"
   - Phải tập trung vào ĐÚNG vấn đề được hỏi

BƯỚC 4: TẠO CÂU TRẢ LỜI

Nếu TÌM THẤY thông tin:
- Trả lời dựa trên tài liệu
- Có thể tổng hợp, so sánh, liệt kê
- Phải TẬP TRUNG vào vấn đề được hỏi

Nếu KHÔNG TÌM THẤY:
- Từ chối rõ ràng
- Dùng câu: "Hiện tài liệu chưa cung cấp thông tin về nội dung này. Bạn nên tham khảo nhân viên y tế để được tư vấn."

==================================================
VÍ DỤ MINH HỌA
==================================================

Ví dụ 1 - Kiểm tra triệu chứng:
Tài liệu: "Triệu chứng đái tháo đường: mệt mỏi, khát nước, tiểu nhiều"
Hỏi: "Mệt mỏi có phải triệu chứng đái tháo đường không?"
✅ Trả lời: "Có. Mệt mỏi là một trong các triệu chứng của đái tháo đường."

Ví dụ 2 - Tìm kiếm ngược:
Tài liệu A: "Cúm: Triệu chứng bao gồm sốt cao, đau đầu..."
Tài liệu B: "Viêm não: Triệu chứng gồm sốt cao, đau đầu dữ dội..."
Hỏi: "Sốt cao và đau đầu là triệu chứng của bệnh gì?"
✅ Trả lời: "Sốt cao và đau đầu có thể xuất hiện trong cúm và viêm não."

Ví dụ 3 - Không có thông tin:
Tài liệu gout: "Triệu chứng: đau khớp ngón chân cái, sưng..."
Hỏi: "Gout có gây đau lưng không?"
✅ Trả lời: "Hiện tài liệu chưa cung cấp thông tin về nội dung này. Bạn nên tham khảo nhân viên y tế để được tư vấn."

Ví dụ 4 - Kiểm tra mối liên hệ có trong tài liệu:
Tài liệu đau lưng: "Nguyên nhân: căng thẳng tâm lý, tư thế xấu..."
Hỏi: "Căng thẳng có gây đau lưng không?"
✅ Trả lời: "Có. Căng thẳng tâm lý là một trong các nguyên nhân gây đau lưng."

==================================================
FORMAT VÀ PHONG CÁCH
==================================================

• Độ dài: 2-4 câu ngắn gọn
• Viết tự nhiên, dễ hiểu
• Đi thẳng vào vấn đề
• Ghi nguồn cuối câu trả lời:

  Nguồn: ten_file.txt

  (Hoặc nếu nhiều tài liệu: Nguồn: file1.txt, file2.txt)

==================================================
QUY TẮC QUAN TRỌNG VỀ NGUỒN (CITATION)
==================================================

⚠️ CHỈ GHI NGUỒN CỦA TÀI LIỆU THỰC SỰ ĐÃ DÙNG:

• Nếu chỉ dùng nội dung từ 1 tài liệu → Chỉ ghi 1 nguồn
• Nếu dùng nội dung từ 2+ tài liệu → Ghi tất cả nguồn đã dùng
• Nếu tài liệu có trong context nhưng KHÔNG dùng → KHÔNG ghi nguồn đó

Ví dụ:

Context có:
- [Tài liệu 1 - dai_thao_duong.txt]: Thông tin về đái tháo đường
- [Tài liệu 2 - beo_phi_do_loi_song.txt]: Thông tin về béo phì

Câu hỏi: "Triệu chứng của đái tháo đường?"
→ CHỈ dùng Tài liệu 1 → Nguồn: dai_thao_duong.txt ✅
→ KHÔNG ghi: Nguồn: dai_thao_duong.txt, beo_phi_do_loi_song.txt ❌

Câu hỏi: "So sánh đái tháo đường và béo phì?"
→ Dùng CẢ HAI tài liệu → Nguồn: dai_thao_duong.txt, beo_phi_do_loi_song.txt ✅
```

**Variables:**

- `{question}` - User's original query
- `{context}` - Formatted retrieved documents (from `format_context()`)

**Safety Rules:**

1. Multi-step reasoning required (analyze → search → infer → respond)
2. Explicit permission for logical operations (list checking, reverse lookup, comparison)
3. Explicit prohibition of external knowledge injection
4. Source citation rules (only cite used documents)
5. Fallback trigger: "Hiện tài liệu chưa cung cấp..."

---

### 3. Context Formatting Function

**Location:** `backend/rag/prompts.py::format_context()`

**Purpose:** Convert retrieved documents into structured context string

**Template:**

```
[Tài liệu 1 - {source}]
{content}
---
[Tài liệu 2 - {source}]
{content}
---
...
```

**Code:**

```python
def format_context(retrieved_docs: list) -> str:
    if not retrieved_docs:
        return "Không có thông tin liên quan."

    context_parts = []
    for i, doc in enumerate(retrieved_docs, 1):
        content = doc.get('content', '')
        metadata = doc.get('metadata', {})
        source = metadata.get('source', 'Unknown')
        context_parts.append(f"[Tài liệu {i} - {source}]\n{content}")

    return "\n---\n".join(context_parts)
```

---

### 4. Message Builder

**Location:** `backend/rag/prompts.py::build_messages()`

**Purpose:** Construct OpenAI-format message array for LLM

**Output Structure:**

```python
[
    {"role": "system", "content": HEALTH_CHATBOT_SYSTEM_PROMPT},
    {"role": "user", "content": "Previous user message"},
    {"role": "assistant", "content": "Previous bot response"},
    ...
    {"role": "user", "content": RAG_PROMPT_TEMPLATE.format(question=..., context=...)}
]
```

---

### 5. Greeting & Farewell Responses

**Location:** `backend/rag/prompts.py`

**Greeting Responses:**

```python
GREETING_RESPONSES = [
    "Xin chào! Tôi có thể hỗ trợ bạn tìm hiểu thông tin sức khỏe.",
]
```

**Greeting Detection:**

```python
def is_greeting(text: str) -> bool:
    greetings = [
        r'\bxin chào\b', r'\bchào\b', r'\bhello\b',
        r'\bhi\b', r'\bhey\b', r'\bchao\b'
    ]
    return any(re.search(pattern, text.lower()) for pattern in greetings)
```

**Farewell Responses:**

```python
FAREWELL_RESPONSES = [
    "Chúc bạn luôn khỏe mạnh!",
]
```

---

### 6. Fallback Responses

**Location:** `backend/rag/prompts.py`

**No Documents Found:**

```python
NO_DOCS_FOUND_RESPONSE = """Hiện tài liệu chưa cung cấp thông tin về nội dung này.
Bạn nên tham khảo nhân viên y tế để được tư vấn."""
```

**Strict Safety Fallback (Policy Violation):**

```python
STRICT_FALLBACK_RESPONSE = """Hiện tài liệu chưa cung cấp thông tin về nội dung này.
Bạn nên tham khảo nhân viên y tế để được tư vấn."""
```

**Usage:** Both fallbacks use same text to avoid revealing detection mechanism

---

### 7. Safety Filter Functions

**Location:** `backend/rag/prompts.py`

**Policy Violation Detector:**

```python
def violates_policy(answer: str) -> bool:
    """Check if answer violates medical advice policy"""
    if not answer:
        return False

    text_lower = answer.lower()

    # Red flags for diagnosis
    diagnosis_flags = [
        "tôi chẩn đoán",
        "bạn bị bệnh",
        "tôi kết luận"
    ]

    return any(flag in text_lower for flag in diagnosis_flags)
```

**Answer Sanitizer:**

```python
def sanitize_answer(answer: str) -> str:
    """Clean answer or return fallback if unsafe"""
    if not answer or not answer.strip():
        return STRICT_FALLBACK_RESPONSE

    if violates_policy(answer):
        return STRICT_FALLBACK_RESPONSE

    return answer
```

**Safety Rules:**

1. Pre-generation: Block medical diagnosis queries (`should_block_query()` in `query_normalizer.py`)
2. Post-generation: Detect diagnosis in LLM output (`violates_policy()`)
3. Fallback: Return safe response if violation detected

---

### 8. Query Normalizer (Pre-RAG Filter)

**Location:** `backend/utils/query_normalizer.py::should_block_query()`

**Purpose:** Block dangerous queries before retrieval

**Blocked Patterns:**

```python
MEDICAL_DIAGNOSIS_PATTERNS = [
    r'\btôi (có |đang )?bị\b.*',
    r'\bcon tôi (có |đang )?bị\b.*',
    r'\bchồng/vợ tôi (có |đang )?bị\b.*',
    r'\bchẩn đoán\b',
    r'\bkết luận bệnh\b'
]
```

**Safety Rules:**

1. Pattern matching on user query
2. Return `(should_block=True, reason)` if matched
3. Chain uses fallback without calling LLM

---

## SECTION 6: API/INTERFACE

### Framework Detection

**Framework:** Flask 3.0.0  
**Entry Point:** `frontend/app.py`  
**Server:** Werkzeug WSGI server (development) / Gunicorn (production recommended)

### Authentication System

**Session Management:**

- **Technology:** Flask sessions with server-side storage
- **Secret Key:** Environment variable `FLASK_SECRET_KEY` (random generated if missing)
- **Session Data:** `user_id`, `username`, `email`, `role`

**User Database:**

- **Primary:** SQL Server (via pyodbc)
- **Schema:**

```sql
CREATE TABLE users (
    id INT PRIMARY KEY IDENTITY(1,1),
    username NVARCHAR(50) UNIQUE NOT NULL,
    email NVARCHAR(100) UNIQUE NOT NULL,
    password_hash NVARCHAR(255) NOT NULL,
    role NVARCHAR(20) DEFAULT 'USER',
    is_active BIT DEFAULT 1,
    created_at DATETIME DEFAULT GETDATE(),
    last_login DATETIME
);
```

**Password Security:**

- Hashing: `werkzeug.security.generate_password_hash()` (PBKDF2)
- Verification: `check_password_hash()`

### Rate Limiting

**Technology:** Flask-Limiter

**Configuration:**

```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour"],
    storage_uri="memory://"  # Use Redis in production
)
```

**Endpoint-Specific Limits:**

- Login: `5 per minute` (brute-force protection)
- Register: `3 per minute` (spam prevention)
- Chat Endpoints: `20 per minute`
- Default: `100 per hour`

### API Endpoints

#### 1. Authentication Endpoints

**POST `/login`**

- **Purpose:** User authentication
- **Rate Limit:** 5 per minute
- **Request Body:**
  ```json
  {
    "username": "user123",
    "password": "password"
  }
  ```
- **Success Response (200):**
  ```json
  {
    "success": true,
    "message": "Đăng nhập thành công!",
    "redirect": "/index"
  }
  ```
- **Error Response (401):**
  ```json
  {
    "success": false,
    "message": "Tài khoản không tồn tại hoặc đã bị khóa"
  }
  ```

**POST `/register`**

- **Purpose:** New user registration
- **Rate Limit:** 3 per minute
- **Request Body:**
  ```json
  {
    "username": "newuser",
    "email": "user@example.com",
    "password": "password123",
    "confirm_password": "password123"
  }
  ```
- **Validation:**
  - Username: min 3 characters
  - Password: min 6 characters
  - Email: valid format with @ and .
  - Passwords must match
- **Success Response (200):**
  ```json
  {
    "success": true,
    "message": "Đăng ký thành công!",
    "redirect": "/login"
  }
  ```

**GET `/logout`**

- **Purpose:** Clear session and redirect to login
- **No Rate Limit**
- **Response:** 302 redirect to `/login`

---

#### 2. Chat Endpoints

**POST `/api/chat`**

- **Purpose:** Synchronous chat (returns full response)
- **Rate Limit:** 20 per minute
- **Authentication:** Required (session-based)
- **Request Body:**
  ```json
  {
    "message": "Triệu chứng của COVID-19 là gì?",
    "session_id": "session_12345"
  }
  ```
- **Response (200):**
  ```json
  {
    "answer": "Triệu chứng của COVID-19 bao gồm sốt, ho khô, mệt mỏi...",
    "sources": ["covid19.txt", "viem_phoi.txt"],
    "session_id": "session_12345"
  }
  ```
- **Error Response (400):**
  ```json
  {
    "error": "Message cannot be empty"
  }
  ```
- **Error Response (500):**
  ```json
  {
    "error": "Groq API error: [details]"
  }
  ```

**POST `/api/chat/stream`**

- **Purpose:** Streaming chat (Server-Sent Events)
- **Rate Limit:** 20 per minute
- **Authentication:** Required
- **Content-Type:** `text/event-stream`
- **Request Body:** Same as `/api/chat`
- **Response Stream:**

  ```
  data: {"type": "token", "content": "Triệu"}

  data: {"type": "token", "content": " chứng"}

  data: {"type": "token", "content": " của"}

  ...

  data: {"type": "sources", "sources": ["covid19.txt"]}

  data: {"type": "done"}
  ```

- **Error Event:**
  ```
  data: {"type": "error", "error": "Rate limit exceeded"}
  ```

---

#### 3. Utility Endpoints

**GET `/api/health`**

- **Purpose:** System health check
- **No Rate Limit**
- **No Authentication Required**
- **Response (200):**
  ```json
  {
    "status": "healthy",
    "vector_store_docs": 45,
    "model": "llama-3.3-70b-versatile"
  }
  ```
- **Error Response (500):**
  ```json
  {
    "status": "unhealthy",
    "error": "Vector store not loaded"
  }
  ```

**POST `/api/clear`**

- **Purpose:** Clear chat history for session
- **No Rate Limit**
- **Authentication:** Required
- **Request Body:**
  ```json
  {
    "session_id": "session_12345"
  }
  ```
- **Response (200):**
  ```json
  {
    "message": "History cleared",
    "session_id": "session_12345"
  }
  ```

**GET `/api/sessions/<session_id>/history`**

- **Purpose:** Retrieve chat history
- **No Rate Limit**
- **Authentication:** Required
- **Response (200):**
  ```json
  {
    "history": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Xin chào!"},
      ...
    ],
    "session_id": "session_12345"
  }
  ```

---

#### 4. Page Routes

**GET `/`**

- **Purpose:** Main chat interface
- **Authentication:** Required (redirects to `/login` if not authenticated)
- **Response:** `templates/index.html`
- **Context:** `username`, `role`

**GET `/login`**

- **Purpose:** Login page
- **No Authentication Required**
- **Response:** `templates/login.html`

**GET `/register`**

- **Purpose:** Registration page
- **No Authentication Required**
- **Response:** `templates/register.html`

---

### Frontend Architecture

**Technology Stack:**

- Vanilla JavaScript (ES6+)
- HTML5 Semantic Markup
- CSS3 with CSS Variables
- No Frontend Framework (lightweight, fast)

**Key Features:**

1. **Server-Sent Events (SSE) Streaming:**

   ```javascript
   async streamResponse(message, typingId) {
       const response = await fetch('/api/chat/stream', {
           method: 'POST',
           headers: {'Content-Type': 'application/json'},
           body: JSON.stringify({message, session_id: this.sessionId})
       });

       const reader = response.body.getReader();
       while (true) {
           const {value, done} = await reader.read();
           if (done) break;

           const data = JSON.parse(line.slice(6));
           if (data.type === 'token') {
               fullAnswer += data.content;
               contentEl.innerHTML = this.formatText(fullAnswer);
           }
       }
   }
   ```

2. **Session Management:**
   - Client-side session ID generation
   - Persistent across page reloads (stored in JS variable)
   - Server-side chat history storage

3. **Real-Time Interaction:**
   - Auto-resizing textarea
   - Character counter (2000 max)
   - Typing indicators
   - Enter to send (Shift+Enter for newline)

4. **UI Components:**
   - Welcome screen with example questions
   - Message bubbles (user/bot)
   - Source attribution pills
   - Error handling overlays

**Responsive Design:**

- Mobile-first CSS
- Breakpoints: 768px (tablet), 1024px (desktop)
- Touch-friendly buttons and inputs

---

### CORS Configuration

```python
from flask_cors import CORS
CORS(app)  # Allow all origins (restrict in production)
```

**Production Recommendation:**

```python
CORS(app,
     origins=["https://yourdomain.com"],
     supports_credentials=True)
```

---

### Deployment Configuration

**Development Server:**

```python
app.run(host='0.0.0.0', port=5000, debug=True)
```

**Production Recommendations:**

1. **WSGI Server:** Gunicorn

   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 frontend.app:app
   ```

2. **Reverse Proxy:** Nginx

   ```nginx
   location / {
       proxy_pass http://127.0.0.1:5000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

3. **Rate Limiting Storage:** Redis

   ```python
   storage_uri="redis://localhost:6379"
   ```

4. **Secret Key Management:**
   ```bash
   export FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```

---

## SECTION 7: SOURCE CODE (Files < 300 Lines)

### 1. run.py (28 lines)

```python
"""
Chatbot Sức Khỏe - Main Entry Point
"""
from frontend.app import app
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

if __name__ == '__main__':
    print("=" * 70)
    print("🏥 CHATBOT SỨC KHỎE - KHỞI ĐỘNG HỆ THỐNG")
    print("=" * 70)
    print("\n⏳ Đang khởi động Flask server...")
    print(f"🌐 Server sẽ chạy tại: http://localhost:5000")
    print(f"📱 Mở trình duyệt và truy cập: http://localhost:5000")
    print("\n💡 Nhấn Ctrl+C để dừng server\n")

    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
```

---

### 2. config/config.py (200 lines - key sections)

```python
"""
Configuration Management - Centralized Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application Configuration"""

    # Base Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    HEALTH_KNOWLEDGE_DIR = DATA_DIR / "health_knowledge"
    VECTOR_STORE_DIR = DATA_DIR / "vector_store"
    LOGS_DIR = BASE_DIR / "logs"

    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment")

    # LLM Configuration
    GROQ_MODEL = "llama-3.3-70b-versatile"
    TEMPERATURE = 0.0  # Strict mode
    MAX_TOKENS = 512

    # RAG Configuration
    TOP_K_RETRIEVAL = 2
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 100
    USE_SECTION_BASED_CHUNKING = True

    # Embeddings
    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_MODEL_VI = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION = 384

    # Thresholds
    RELEVANCE_THRESHOLD_L2 = 150.0
    SEMANTIC_THRESHOLD = 0.25
    KEYWORD_BOOST_FACTOR = 0.60
    PRIMARY_MATCH_BOOST_FACTOR = 0.40

    # Database (SQL Server)
    SQL_SERVER = os.getenv("SQL_SERVER", "localhost")
    SQL_DATABASE = os.getenv("SQL_DATABASE", "HealthChatbot")
    SQL_USERNAME = os.getenv("SQL_USERNAME", "sa")
    SQL_PASSWORD = os.getenv("SQL_PASSWORD", "")

    # Logging
    DEBUG = True
    LOG_LEVEL = "INFO"

    # Create directories
    for directory in [DATA_DIR, HEALTH_KNOWLEDGE_DIR, VECTOR_STORE_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

config = Config()
```

---

### 3. backend/utils/logger.py (65 lines)

```python
"""
Centralized Logging Configuration
"""
import logging
from pathlib import Path
from datetime import datetime
from config.config import config

def get_logger(name: str) -> logging.Logger:
    """
    Get or create logger with standardized configuration

    Args:
        name: Logger name (usually __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG if config.DEBUG else logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)

    # File handler
    log_file = config.LOGS_DIR / f"chatbot_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger
```

---

### 4. backend/utils/query_normalizer.py (120 lines - key sections)

```python
"""
Query Normalization and Safety Filtering
"""
import re
from typing import Tuple
from backend.utils.logger import get_logger

logger = get_logger(__name__)

# Blocked diagnostic patterns
MEDICAL_DIAGNOSIS_PATTERNS = [
    r'\btôi (có |đang )?bị\b.*sốt.*ho',
    r'\bcon tôi (có |đang )?bị\b.*',
    r'\bchẩn đoán\b',
    r'\bkết luận bệnh\b',
    r'\btôi mắc bệnh gì\b'
]

def should_block_query(query: str) -> Tuple[bool, str]:
    """
    Check if query should be blocked (diagnosis seeking)

    Args:
        query: User query

    Returns:
        Tuple[bool, str]: (should_block, reason)
    """
    if not query:
        return False, ""

    query_lower = query.lower().strip()

    for pattern in MEDICAL_DIAGNOSIS_PATTERNS:
        if re.search(pattern, query_lower):
            logger.warning(f"Blocked query pattern: {pattern}")
            return True, f"Pattern matched: {pattern}"

    return False, ""

def normalize_query(query: str) -> str:
    """
    Normalize query for better retrieval

    Args:
        query: Raw user query

    Returns:
        str: Normalized query
    """
    if not query:
        return ""

    # Remove extra whitespace
    query = re.sub(r'\s+', ' ', query).strip()

    # Expand abbreviations (Vietnamese)
    abbreviations = {
        'covid': 'covid-19',
        'dttd': 'đái tháo đường',
        'th': 'tăng huyết áp'
    }

    for abbr, full in abbreviations.items():
        query = re.sub(r'\b' + abbr + r'\b', full, query, flags=re.IGNORECASE)

    return query
```

---

### 5. scripts/build_vector_db.py (180 lines - simplified)

```python
"""
Vector Database Builder - Rebuild FAISS Index from Documents
"""
from backend.utils.document_loader import DocumentLoader
from backend.utils.chunking import DocumentChunker
from backend.rag.embeddings import EmbeddingModel
from backend.database.vector_store import VectorStore
from config.config import config
from pathlib import Path

def build_vector_database():
    """Main build pipeline"""
    print("=" * 70)
    print("🏗️  BUILDING VECTOR DATABASE")
    print("=" * 70)

    # Step 1: Load documents
    print("\n📂 Step 1: Loading documents...")
    loader = DocumentLoader()
    documents = loader.load_directory(
        str(config.HEALTH_KNOWLEDGE_DIR),
        recursive=False
    )
    print(f"✅ Loaded {len(documents)} documents")

    # Step 2: Chunk documents
    print("\n✂️  Step 2: Chunking documents...")
    chunker = DocumentChunker(use_section_based=True)
    chunks = chunker.chunk_documents(documents)
    print(f"✅ Created {len(chunks)} chunks")

    # Step 3: Generate embeddings
    print("\n🧮 Step 3: Generating embeddings...")
    embedder = EmbeddingModel(use_vietnamese=True)
    chunks_with_embeddings = embedder.encode_documents(chunks)
    print(f"✅ Generated {len(chunks_with_embeddings)} embeddings")

    # Step 4: Build FAISS index
    print("\n🔨 Step 4: Building FAISS index...")
    vector_store = VectorStore(dimension=embedder.embedding_dim)
    vector_store.add_documents(chunks_with_embeddings)

    # Step 5: Save
    print("\n💾 Step 5: Saving vector store...")
    save_path = str(config.VECTOR_STORE_DIR / "health_faiss.index")
    vector_store.save(save_path)

    print("\n" + "=" * 70)
    print("✅ VECTOR DATABASE BUILD COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Statistics:")
    print(f"  - Documents: {len(documents)}")
    print(f"  - Chunks: {len(chunks)}")
    print(f"  - Embedding dimension: {embedder.embedding_dim}")
    print(f"  - Index path: {save_path}")

if __name__ == "__main__":
    build_vector_database()
```

---

### 6. scripts/validate_content.py (145 lines - simplified)

```python
"""
Content Validation - Check document standardization
"""
from pathlib import Path
from config.config import config
import re

REQUIRED_SECTIONS = [
    "1. Tổng quan",
    "2. Dấu hiệu nhận biết",
    "3. Nguyên nhân",
    "4. Ảnh hưởng đến sức khỏe",
    "5. Chăm sóc & hỗ trợ tại nhà",
    "6. Phòng ngừa",
    "7. Khi nào cần đi khám",
    "8. Lưu ý quan trọng"
]

def validate_document(filepath: Path) -> dict:
    """
    Validate document structure

    Returns:
        dict: {'valid': bool, 'missing_sections': list, 'issues': list}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    missing_sections = []
    for section in REQUIRED_SECTIONS:
        if section not in content:
            missing_sections.append(section)

    issues = []
    if not missing_sections:
        # Check section order
        positions = {}
        for section in REQUIRED_SECTIONS:
            pos = content.find(section)
            if pos != -1:
                positions[section] = pos

        sorted_positions = sorted(positions.items(), key=lambda x: x[1])
        for i, (section, pos) in enumerate(sorted_positions):
            if section != REQUIRED_SECTIONS[i]:
                issues.append(f"Section order incorrect: {section}")

    return {
        'valid': len(missing_sections) == 0 and len(issues) == 0,
        'missing_sections': missing_sections,
        'issues': issues
    }

def validate_all_documents():
    """Validate all documents in health_knowledge directory"""
    print("=" * 70)
    print("📋 VALIDATING HEALTH DOCUMENTS")
    print("=" * 70)

    docs_dir = config.HEALTH_KNOWLEDGE_DIR
    total = 0
    valid = 0
    invalid = 0

    for filepath in sorted(docs_dir.glob("*.txt")):
        total += 1
        result = validate_document(filepath)

        if result['valid']:
            valid += 1
            print(f"✅ {filepath.name}")
        else:
            invalid += 1
            print(f"❌ {filepath.name}")
            if result['missing_sections']:
                print(f"   Missing: {', '.join(result['missing_sections'])}")
            if result['issues']:
                for issue in result['issues']:
                    print(f"   Issue: {issue}")

    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {valid}/{total} documents valid ({invalid} need fixing)")
    print("=" * 70)

if __name__ == "__main__":
    validate_all_documents()
```

---

### 7. rebuild_database.bat (Windows Batch Script)

```batch
@echo off
echo ========================================
echo REBUILDING VECTOR DATABASE
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run rebuild script
python rebuild_vector_database.py

echo.
echo ========================================
echo DATABASE REBUILD COMPLETE
echo ========================================
pause
```

---

### 8. start_chatbot.bat (Windows Startup Script)

```batch
@echo off
echo ========================================
echo STARTING HEALTH CHATBOT
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if vector store exists
if not exist "data\vector_store\health_faiss.index.faiss" (
    echo ERROR: Vector store not found!
    echo Please run rebuild_database.bat first
    pause
    exit
)

REM Start Flask app
echo Starting Flask server...
python run.py

pause
```

---

### 9. requirements.txt (50 lines)

```
# Core Framework
flask>=3.0.0
flask-cors>=4.0.0
flask-limiter>=3.5.0

# LangChain Ecosystem
langchain>=0.2.0
langchain-community>=0.2.0
langchain-groq>=0.1.0

# LLM & Embeddings
groq>=0.5.0
sentence-transformers>=2.3.1
torch>=2.2.0
transformers>=4.30.0

# Vector Database
faiss-cpu>=1.7.4

# Document Processing
pypdf>=4.0.0
python-docx>=1.1.0
unstructured>=0.12.0
pdfplumber>=0.10.0

# Database
pyodbc>=5.0.0
sqlalchemy>=2.0.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.5.0
numpy>=1.24.0
pandas>=2.0.0

# Security
werkzeug>=3.0.0

# Development
ipython>=8.12.0
jupyterlab>=4.0.0
pytest>=7.4.0
```

---

## SUMMARY & RECOMMENDATIONS

### System Strengths

1. **Strict RAG Architecture:** TEMPERATURE=0.0 + post-generation filtering prevents hallucination
2. **Section-Based Chunking:** Preserves medical document structure better than fixed-size chunks
3. **Vietnamese Optimization:** Multilingual embeddings + accent normalization + high L2 threshold (150.0)
4. **Multi-Level Safety:** Pre-RAG query blocking + post-generation sanitization
5. **Keyword Boosting:** Improved topical relevance for disease-specific queries (60% boost for primary matches)
6. **Authentication & Rate Limiting:** Production-ready security controls
7. **Streaming Interface:** Real-time SSE for better UX

### Areas for Improvement

1. **Reranker:** Consider adding cross-encoder reranking for improved precision (e.g., `ms-marco-MiniLM-L-12-v2`)
2. **Cache Layer:** Implement Redis for:
   - Rate limiting storage (currently in-memory)
   - Chat history persistence
   - Embedding cache sharing across instances
3. **Vector DB Scaling:** Migrate to FAISS IndexIVFFlat or Milvus when document count exceeds 1000
4. **Monitoring:** Add Prometheus metrics for:
   - Query latency
   - Retrieval accuracy
   - LLM API usage
5. **Testing:** Expand unit tests for retrieval quality and safety filters
6. **Documentation:** Generate API docs with Swagger/OpenAPI

### Deployment Checklist

- [ ] Set `FLASK_SECRET_KEY` environment variable
- [ ] Configure production WSGI server (Gunicorn)
- [ ] Set up Nginx reverse proxy
- [ ] Migrate rate limiting to Redis
- [ ] Enable HTTPS with SSL certificate
- [ ] Configure CORS for production domain
- [ ] Set up database backups (SQL Server maintenance plan)
- [ ] Implement log rotation (logrotate)
- [ ] Monitor Groq API quota usage
- [ ] Set up health check monitoring (UptimeRobot/PingdomOpsgenie)

---

**Document END**  
**Total Sections:** 7  
**Total Pages:** ~35 (estimated)  
**Last Updated:** 2025-01-26
