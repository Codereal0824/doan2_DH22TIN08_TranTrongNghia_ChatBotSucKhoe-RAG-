"""
Text Chunking - Chia nhỏ văn bản thành các đoạn để xử lý RAG
"""
from config.config import config
from typing import List, Dict
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sys
from pathlib import Path
import re

# Thêm path để import config
sys.path.append(str(Path(__file__).parent.parent.parent))


# ============================================
# SECTION-BASED CHUNKER (NEW)
# ============================================

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
        # Pattern để nhận diện section headers (1. , 2. , 3. , ...)
        self.section_pattern = re.compile(r'^\d+\.\s+(.+)$', re.MULTILINE)

        # HYBRID: RecursiveCharacterTextSplitter cho section quá dài
        self.chunk_size = chunk_size
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
            length_function=len,
        )

    def extract_title(self, text: str) -> str:
        """
        Trích xuất tiêu đề tài liệu (thường là dòng đầu tiên)

        Args:
            text: Toàn bộ văn bản

        Returns:
            str: Tiêu đề hoặc empty string
        """
        lines = text.strip().split('\n')

        # Tìm dòng có "Tiêu đề:"
        for line in lines[:10]:  # Chỉ tìm trong 10 dòng đầu
            if line.strip().startswith('Tiêu đề:'):
                return line.strip().replace('Tiêu đề:', '').strip()

        # Nếu không tìm thấy, lấy dòng đầu tiên không rỗng
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

        # Extract document title
        doc_title = self.extract_title(text)

        # Find all section headers
        sections = []
        lines = text.split('\n')

        current_section = None
        current_section_title = None
        current_content = []

        for line in lines:
            # Check if line is a section header (1. , 2. , 3. , ...)
            match = re.match(r'^(\d+)\.\s+(.+)$', line.strip())

            if match:
                # Save previous section if exists
                if current_section is not None:
                    section_text = '\n'.join(current_content).strip()
                    if section_text:
                        sections.append({
                            'number': current_section,
                            'title': current_section_title,
                            'content': section_text
                        })

                # Start new section
                current_section = match.group(1)
                current_section_title = match.group(2).strip()
                current_content = []
            else:
                # Add line to current section content
                if current_section is not None:
                    current_content.append(line)

        # Save last section
        if current_section is not None:
            section_text = '\n'.join(current_content).strip()
            if section_text:
                sections.append({
                    'number': current_section,
                    'title': current_section_title,
                    'content': section_text
                })

        # Create chunks from sections
        chunks = []
        for i, section in enumerate(sections):
            # Format: "Document Title - Section Title:\n Content"
            if doc_title:
                chunk_text = f"{doc_title} - {section['title']}:\n\n{section['content']}"
            else:
                chunk_text = f"{section['title']}:\n\n{section['content']}"

            # ============================================
            # HYBRID CHUNKING: Chia nhỏ section nếu quá dài
            # ============================================
            if len(chunk_text) > self.chunk_size:
                # Section vượt quá giới hạn -> Chia nhỏ bằng RecursiveCharacterTextSplitter
                print(
                    f"   ⚠️  Section '{section['title']}' quá dài ({len(chunk_text)} chars), đang chia nhỏ...")

                sub_chunks_text = self.text_splitter.split_text(chunk_text)

                for sub_idx, sub_chunk_text in enumerate(sub_chunks_text):
                    # Tạo metadata cho sub-chunk
                    chunk_metadata = metadata.copy() if metadata else {}
                    chunk_metadata['chunk_index'] = len(
                        chunks)  # Global chunk index
                    chunk_metadata['section_number'] = section['number']
                    chunk_metadata['section_title'] = section['title']
                    chunk_metadata['document_title'] = doc_title
                    chunk_metadata['chunking_method'] = 'hybrid-section-recursive'
                    # Sub-chunk index trong section
                    chunk_metadata['sub_chunk_index'] = sub_idx
                    chunk_metadata['total_sub_chunks'] = len(sub_chunks_text)

                    chunks.append({
                        'content': sub_chunk_text,
                        'metadata': chunk_metadata
                    })
            else:
                # Section đủ ngắn -> Giữ nguyên
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

        # Cập nhật total_chunks cho tất cả chunks
        for chunk in chunks:
            chunk['metadata']['total_chunks'] = len(chunks)

        return chunks


class DocumentChunker:
    """Class để chia nhỏ documents thành chunks"""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None,
        use_section_based: bool = True  # NEW: Default to section-based
    ):
        """
        Khởi tạo chunker

        Args:
            chunk_size: Kích thước tối đa của mỗi chunk (characters)
            chunk_overlap: Số ký tự chồng lấp giữa các chunk
            separators: Danh sách ký tự phân tách ưu tiên
            use_section_based: Sử dụng section-based chunking (khuyên dùng)
        """
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP
        self.use_section_based = use_section_based

        # Initialize section-based chunker với Hybrid strategy
        self.section_chunker = SectionBasedChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        # Separators cho tiếng Việt (fallback cho non-section chunking)
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
            f"📊 Chunking mode: {'Section-Based' if use_section_based else 'Token-Based'}")

    def chunk_text(self, text: str, metadata: Dict = None) -> List[Dict]:
        """
        Chia một văn bản thành nhiều chunks

        Args:
            text: Văn bản cần chia
            metadata: Metadata gắn với văn bản

        Returns:
            List[Dict]: Danh sách chunks với content và metadata
        """
        if not text or not text.strip():
            return []

        # ============================================
        # TRY SECTION-BASED CHUNKING FIRST
        # ============================================
        if self.use_section_based:
            # Kiểm tra xem văn bản có cấu trúc section không
            section_chunks = self.section_chunker.chunk_by_sections(
                text, metadata)

            if section_chunks and len(section_chunks) > 0:
                print(
                    f"   ✅ Section-based chunking: {len(section_chunks)} sections")
                return section_chunks
            else:
                print("   ⚠️  No sections found, falling back to token-based chunking")

        # ============================================
        # FALLBACK: TOKEN-BASED CHUNKING
        # ============================================
        chunks = self.text_splitter.split_text(text)

        # Tạo list documents
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

        print(f"   ✅ Token-based chunking: {len(documents)} chunks")
        return documents

    def chunk_documents(self, documents: List[Dict]) -> List[Dict]:
        """
        Chia nhiều documents thành chunks

        Args:
            documents: Danh sách documents với format:
                      [{'content': str, 'metadata': dict}, ...]

        Returns:
            List[Dict]: Danh sách chunks
        """
        all_chunks = []

        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})

            chunks = self.chunk_text(content, metadata)
            all_chunks.extend(chunks)

        return all_chunks
