"""
Text Chunking - Chia nhỏ văn bản thành các đoạn để xử lý RAG
"""
from config.config import config
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sys
from pathlib import Path
import re

# Thêm path để import config từ thư mục gốc
sys.path.append(str(Path(__file__).parent.parent.parent))


# ============================================
# SECTION-BASED CHUNKER (CHIA NHỎ DỮ LIỆU THEO NGỮ NGHĨA)
# ============================================

# Lớp này triển khai thuật toán Semantic Chunking.
# Khác với Naive Chunking (chia theo số lượng ký tự cố định), thuật toán này
# nhận diện cấu trúc logic của văn bản y khoa (các mục 1, 2, 3...) để đảm bảo
# LLM nhận được một khối thông tin trọn vẹn ý nghĩa nhất.
class SectionBasedChunker:
    """
    Chunker chia tài liệu theo cấu trúc section (1., 2., 3., ...)
    Mỗi section thành một chunk hoàn chỉnh với tiêu đề + nội dung

    UPDATED: Hybrid Chunking - Nếu section quá dài (>CHUNK_SIZE), 
    tự động chia nhỏ bằng RecursiveCharacterTextSplitter
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Khởi tạo section-based chunker với Hybrid strategy

        Args:
            chunk_size: Kích thước tối đa cho mỗi chunk (chars)
            chunk_overlap: Độ chồng lấp giữa các sub-chunks
        """
        # Biểu thức chính quy (Regex) để nhận diện các tiêu đề mục.
        # Sử dụng cờ re.MULTILINE để áp dụng mẫu tìm kiếm cho từng dòng độc lập.
        self.section_pattern = re.compile(r'^\d+\.\s+(.+)$', re.MULTILINE)

        # CƠ CHẾ LAI (HYBRID CHUNKING):
        # Khởi tạo một đối tượng chia văn bản đệ quy dự phòng.
        # Nếu một mục (Section) có nội dung quá dài vượt giới hạn Token,
        # nó sẽ bị cắt nhỏ dựa trên các dấu câu (chấm, phẩy) để bảo toàn cấu trúc ngữ pháp.
        self.chunk_size = chunk_size
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            length_function=len,
        )

    # Thuật toán Heuristic (Kinh nghiệm) để trích xuất tiêu đề văn bản.
    def extract_title(self, text: str) -> str:
        """
        Trích xuất tiêu đề tài liệu (thường là dòng đầu tiên)

        Args:
            text: Toàn bộ văn bản

        Returns:
            str: Tiêu đề hoặc empty string
        """
        lines = text.strip().split('\n')

        # Quét 10 dòng đầu tiên để tìm từ khóa định danh "Tiêu đề:"
        for line in lines[:10]:
            if line.strip().startswith('Tiêu đề:'):
                return line.strip().replace('Tiêu đề:', '').strip()

        # Fallback: Nếu không có từ khóa định danh, giả định dòng văn bản
        # đầu tiên không rỗng (và không phải dòng trích dẫn nguồn) là Tiêu đề.
        for line in lines[:5]:
            if line.strip() and not line.strip().startswith('Nguồn:'):
                return line.strip()

        return ""

    def chunk_by_sections(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Chia văn bản theo sections (1., 2., 3., ...)

        Args:
            text: Văn bản cần chia
            metadata: Metadata gắn với văn bản

        Returns:
            List[Dict]: Danh sách chunks, mỗi chunk là một section hoàn chỉnh
        """
        if not text or not text.strip():
            return []

        doc_title = self.extract_title(text)

        sections = []
        lines = text.split('\n')

        current_section = None
        current_section_title = None
        current_content = []

        # Máy trạng thái hữu hạn (Finite State Machine) đơn giản để duyệt từng dòng
        # và gom cụm nội dung thuộc về cùng một Section.
        for line in lines:
            match = re.match(r'^(\d+)\.\s+(.+)$', line.strip())

            if match:
                # Khi gặp một tiêu đề mới, tiến hành đóng gói (Save) nội dung của mục cũ
                if current_section is not None:
                    section_text = '\n'.join(current_content).strip()
                    if section_text:
                        sections.append({
                            'number': current_section,
                            'title': current_section_title,
                            'content': section_text
                        })

                # Bắt đầu ghi nhận dữ liệu cho mục mới
                current_section = match.group(1)
                current_section_title = match.group(2).strip()
                current_content = []
            else:
                # Tích lũy nội dung văn bản vào mục hiện tại
                if current_section is not None:
                    current_content.append(line)

        # Xử lý trường hợp biên (Edge Case): Lưu lại mục cuối cùng khi kết thúc vòng lặp
        if current_section is not None:
            section_text = '\n'.join(current_content).strip()
            if section_text:
                sections.append({
                    'number': current_section,
                    'title': current_section_title,
                    'content': section_text
                })

        chunks = []
        for i, section in enumerate(sections):
            # Kỹ thuật Metadata Enrichment (Làm giàu Siêu dữ liệu):
            # Cố tình ghép nối Tên tài liệu + Tên mục vào nội dung văn bản.
            # Điều này giúp các đoạn văn bản (chunks) đứng độc lập vẫn giữ được Context.
            if doc_title:
                chunk_text = f"{doc_title} - {section['title']}:\n\n{section['content']}"
            else:
                chunk_text = f"{section['title']}:\n\n{section['content']}"

            # ============================================
            # HYBRID CHUNKING: KIỂM SOÁT KÍCH THƯỚC (SIZE CONTROL)
            # ============================================
            if len(chunk_text) > self.chunk_size:
                print(
                    f" [CANH BAO] Section '{section['title']}' qua dai ({len(chunk_text)} chars), dang chia nho...")

                sub_chunks_text = self.text_splitter.split_text(chunk_text)

                for sub_idx, sub_chunk_text in enumerate(sub_chunks_text):
                    # Gắn thẻ (Tagging) chi tiết cho từng sub-chunk để phục vụ công tác Debug
                    # và đối chiếu nguồn sau này.
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata['chunk_index'] = len(chunks)
                    chunk_metadata['section_number'] = section['number']
                    chunk_metadata['section_title'] = section['title']
                    chunk_metadata['document_title'] = doc_title
                    chunk_metadata['chunking_method'] = 'hybrid-section-recursive'
                    chunk_metadata['sub_chunk_index'] = sub_idx
                    chunk_metadata['total_sub_chunks'] = len(sub_chunks_text)

                    chunks.append({
                        'content': sub_chunk_text,
                        'metadata': chunk_metadata
                    })
            else:
                # Nếu kích thước nằm trong ngưỡng an toàn, duy trì tính nguyên vẹn của chunk.
                chunk_metadata = metadata.copy() if metadata else {}
                chunk_metadata['chunk_index'] = len(chunks)
                chunk_metadata['section_number'] = section['number']
                chunk_metadata['section_title'] = section['title']
                chunk_metadata['document_title'] = doc_title
                chunk_metadata['chunking_method'] = 'section-based'

                chunks.append({
                    'content': chunk_text,
                    'metadata': chunk_metadata
                })

        # Cập nhật số lượng tổng để quản lý vòng đời tài liệu
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = len(chunks)

        return chunks

# Lớp DocumentChunker đóng vai trò là Trình điều phối (Orchestrator)
# quyết định việc sử dụng thuật toán chia nhỏ nào tùy thuộc vào cấu trúc của file đầu vào.


class DocumentChunker:
    """Class để chia nhỏ documents thành chunks"""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None,
        use_section_based: bool = True
    ):
        """Khởi tạo chunker"""
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        self.use_section_based = use_section_based

        self.section_chunker = SectionBasedChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        # Cấu hình danh sách ký tự phân tách giảm dần (từ đoạn văn -> câu -> từ).
        # Đảm bảo việc cắt chuỗi không làm hỏng cụm từ tiếng Việt.
        if separators is None:
            separators = [
                "\n\n",  # Paragraph
                "\n",    # New line
                ". ",    # Sentence end
                "! ",    # Exclamation
                "? ",    # Question
                "; ",    # Semicolon
                ", ",    # Comma
                " ",     # Space
                ""       # Character
            ]

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=separators,
            length_function=len,
        )

        print(
            f"[THONG TIN] Chunking mode: {'Section-Based' if use_section_based else 'Token-Based'}")

    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """Chia một văn bản thành nhiều chunks"""
        if not text or not text.strip():
            return []

        # ============================================
        # ƯU TIÊN SỬ DỤNG SECTION-BASED CHUNKING (SEMANTIC)
        # ============================================
        if self.use_section_based:
            section_chunks = self.section_chunker.chunk_by_sections(
                text, metadata)

            if section_chunks and len(section_chunks) > 0:
                print(
                    f"  [THONG TIN] Section-based chunking: {len(section_chunks)} sections")
                return section_chunks
            else:
                print(
                    "  [CANH BAO] No sections found, falling back to token-based chunking")

        # ============================================
        # DỰ PHÒNG: TOKEN-BASED CHUNKING (NAIVE)
        # Nếu tài liệu không có cấu trúc phân mục 1. 2. 3., chuyển về cắt đệ quy.
        # ============================================
        chunks = self.text_splitter.split_text(text)

        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = metadata.copy() if metadata else {}
            doc_metadata['chunk_index'] = i
            doc_metadata['total_chunks'] = len(chunks)
            doc_metadata['chunking_method'] = 'token-based'

            documents.append({
                'content': chunk,
                'metadata': doc_metadata
            })

        print(f"  [THONG TIN] Token-based chunking: {len(documents)} chunks")
        return documents

    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Chia nhiều documents thành chunks
        Hàm hỗ trợ xử lý hàng loạt (Batch Processing).
        """
        all_chunks = []

        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})

            chunks = self.chunk_text(content, metadata)
            all_chunks.extend(chunks)

        return all_chunks
