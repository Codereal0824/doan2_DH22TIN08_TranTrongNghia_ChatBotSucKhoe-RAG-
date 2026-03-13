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

    def chunk_by_sentences(
        self,
        text: str,
        sentences_per_chunk: int = 5,
        metadata: Dict = None
    ) -> List[Dict]:
        """
        Chia văn bản theo số câu

        Args:
            text: Văn bản cần chia
            sentences_per_chunk: Số câu mỗi chunk
            metadata: Metadata

        Returns:
            List[Dict]: Danh sách chunks
        """
        # Tách câu (đơn giản)
        sentences = []
        for sep in ['. ', '! ', '? ']:
            if sep in text:
                text = text.replace(sep, sep + '<<<SPLIT>>>')

        sentences = text.split('<<<SPLIT>>>')
        sentences = [s.strip() for s in sentences if s.strip()]

        # Nhóm câu thành chunks
        chunks = []
        for i in range(0, len(sentences), sentences_per_chunk):
            chunk_sentences = sentences[i:i + sentences_per_chunk]
            chunk_text = ' '.join(chunk_sentences)

            doc_metadata = metadata.copy() if metadata else {}
            doc_metadata['chunk_index'] = len(chunks)
            doc_metadata['sentence_start'] = i
            doc_metadata['sentence_end'] = min(
                i + sentences_per_chunk, len(sentences))

            chunks.append({
                'content': chunk_text,
                'metadata': doc_metadata
            })

        return chunks


def demo_chunking():
    """Demo chức năng chunking"""
    print("=" * 60)
    print("DEMO - DOCUMENT CHUNKING")
    print("=" * 60)

    # Tạo chunker
    chunker = DocumentChunker(chunk_size=200, chunk_overlap=50)

    # Text mẫu
    sample_text = """
    Cảm cúm là bệnh nhiễm virus cúm, lây lan qua đường hô hấp. 
    Bệnh thường xuất hiện vào mùa đông khi thời tiết lạnh.
    
    Triệu chứng phổ biến bao gồm:
    - Sốt cao đột ngột (38-40°C)
    - Đau đầu và đau cơ
    - Đau họng và ho
    - Mệt mỏi toàn thân
    - Chảy nước mũi hoặc nghẹt mũi
    
    Cách phòng ngừa hiệu quả:
    1. Rửa tay thường xuyên bằng xà phòng
    2. Đeo khẩu trang khi ra nơi đông người
    3. Tăng cường hệ miễn dịch qua ăn uống và vận động
    4. Tiêm vaccine phòng cúm hàng năm
    5. Tránh tiếp xúc gần với người bệnh
    
    Khi nào cần đi khám bác sĩ:
    - Sốt cao trên 39°C kéo dài >3 ngày
    - Khó thở, đau ngực
    - Triệu chứng nặng hơn sau vài ngày điều trị
    - Người cao tuổi, trẻ em nhỏ, phụ nữ mang thai
    """

    metadata = {
        'source': 'health_guide.pdf',
        'topic': 'Cảm cúm',
        'page': 15
    }

    # Chunk văn bản
    chunks = chunker.chunk_text(sample_text, metadata)

    print("\n📊 Kết quả:")
    print(f"  - Chunk size: {chunker.chunk_size}")
    print(f"  - Chunk overlap: {chunker.chunk_overlap}")
    print(f"  - Số chunks tạo ra: {len(chunks)}")

    print("\n📄 Chi tiết các chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}/{len(chunks)}:")
        print(f"  Độ dài: {len(chunk['content'])} ký tự")
        print(f"  Metadata: {chunk['metadata']}")
        print("  Nội dung:")
        print("  ---")
        print(f"  {chunk['content'][:150]}...")
        print()

    # Demo chunk theo câu
    print("\n" + "=" * 60)
    print("DEMO - CHUNKING THEO CÂU")
    print("=" * 60)

    short_text = "Đau đầu có thể do nhiều nguyên nhân. Căng thẳng là nguyên nhân phổ biến. Mất ngủ cũng gây đau đầu. Uống ít nước khiến đau đầu tăng. Cần nghỉ ngơi và uống đủ nước."

    sentence_chunks = chunker.chunk_by_sentences(
        short_text,
        sentences_per_chunk=2,
        metadata={'source': 'tips.txt'}
    )

    print("\n📊 Kết quả:")
    print(f"  Số chunks: {len(sentence_chunks)}")

    for i, chunk in enumerate(sentence_chunks, 1):
        print(f"\nChunk {i}:")
        print(f"  {chunk['content']}")
        print(
            f"  Câu từ {chunk['metadata']['sentence_start']} đến {chunk['metadata']['sentence_end']}")


if __name__ == "__main__":
    demo_chunking()
