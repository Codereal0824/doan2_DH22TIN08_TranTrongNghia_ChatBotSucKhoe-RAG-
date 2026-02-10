"""
Text Chunking - Chia nhỏ văn bản thành các đoạn để xử lý RAG
"""
from config.config import config
from typing import List, Dict
from langchain.text_splitter import RecursiveCharacterTextSplitter
import sys
from pathlib import Path

# Thêm path để import config
sys.path.append(str(Path(__file__).parent.parent.parent))


class DocumentChunker:
    """Class để chia nhỏ documents thành chunks"""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None
    ):
        """
        Khởi tạo chunker

        Args:
            chunk_size: Kích thước tối đa của mỗi chunk (characters)
            chunk_overlap: Số ký tự chồng lấp giữa các chunk
            separators: Danh sách ký tự phân tách ưu tiên
        """
        self.chunk_size = chunk_size or config.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.CHUNK_OVERLAP

        # Separators cho tiếng Việt
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

        # Chia văn bản
        chunks = self.text_splitter.split_text(text)

        # Tạo list documents
        documents = []
        for i, chunk in enumerate(chunks):
            doc_metadata = metadata.copy() if metadata else {}
            doc_metadata['chunk_index'] = i
            doc_metadata['total_chunks'] = len(chunks)

            documents.append({
                'content': chunk,
                'metadata': doc_metadata
            })

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

    print(f"\n📊 Kết quả:")
    print(f"  - Chunk size: {chunker.chunk_size}")
    print(f"  - Chunk overlap: {chunker.chunk_overlap}")
    print(f"  - Số chunks tạo ra: {len(chunks)}")

    print(f"\n📄 Chi tiết các chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}/{len(chunks)}:")
        print(f"  Độ dài: {len(chunk['content'])} ký tự")
        print(f"  Metadata: {chunk['metadata']}")
        print(f"  Nội dung:")
        print(f"  ---")
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

    print(f"\n📊 Kết quả:")
    print(f"  Số chunks: {len(sentence_chunks)}")

    for i, chunk in enumerate(sentence_chunks, 1):
        print(f"\nChunk {i}:")
        print(f"  {chunk['content']}")
        print(
            f"  Câu từ {chunk['metadata']['sentence_start']} đến {chunk['metadata']['sentence_end']}")


if __name__ == "__main__":
    demo_chunking()
