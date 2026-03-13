"""
Document Loader - Đọc và xử lý tài liệu PDF, Word, Text
"""
from config.config import config
from pathlib import Path
from typing import List, Dict
import sys

# PDF
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except:
    HAS_PYPDF = False

# Word
try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except:
    HAS_DOCX = False

# Thêm path để import config
sys.path.append(str(Path(__file__).parent.parent.parent))


class DocumentLoader:
    """Class để load documents từ nhiều định dạng"""

    def __init__(self):
        """Khởi tạo loader"""
        self.supported_formats = []

        if HAS_PYPDF:
            self.supported_formats.append('.pdf')
        if HAS_DOCX:
            self.supported_formats.extend(['.docx', '.doc'])
        self.supported_formats.extend(['.txt', '.md'])

        print("✅ Document Loader sẵn sàng")
        print(f"📂 Hỗ trợ: {', '.join(self.supported_formats)}")

    def load_pdf(self, file_path: str) -> Dict:
        """
        Đọc file PDF

        Args:
            file_path: Đường dẫn file PDF

        Returns:
            Dict: {'content': str, 'metadata': dict}
        """
        if not HAS_PYPDF:
            raise ImportError("Chưa cài đặt pypdf! Run: pip install pypdf")

        try:
            reader = PdfReader(file_path)

            # Đọc tất cả trang
            content = ""
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text()
                if text:
                    content += f"\n--- Trang {page_num} ---\n{text}"

            metadata = {
                'source': Path(file_path).name,
                'file_path': str(file_path),
                'type': 'pdf',
                'pages': len(reader.pages),
                'format': 'PDF'
            }

            # Thêm metadata từ PDF (nếu có)
            if reader.metadata:
                if reader.metadata.title:
                    metadata['title'] = reader.metadata.title
                if reader.metadata.author:
                    metadata['author'] = reader.metadata.author

            print(
                f"✅ Đã đọc PDF: {Path(file_path).name} ({len(reader.pages)} trang)")

            return {
                'content': content.strip(),
                'metadata': metadata
            }

        except Exception as e:
            print(f"❌ Lỗi đọc PDF {file_path}: {e}")
            return {'content': '', 'metadata': {'error': str(e)}}

    def load_docx(self, file_path: str) -> Dict:
        """
        Đọc file Word (.docx)

        Args:
            file_path: Đường dẫn file Word

        Returns:
            Dict: {'content': str, 'metadata': dict}
        """
        if not HAS_DOCX:
            raise ImportError(
                "Chưa cài đặt python-docx! Run: pip install python-docx")

        try:
            doc = DocxDocument(file_path)

            # Đọc tất cả paragraphs
            content = "\n".join(
                [para.text for para in doc.paragraphs if para.text.strip()])

            metadata = {
                'source': Path(file_path).name,
                'file_path': str(file_path),
                'type': 'docx',
                'paragraphs': len(doc.paragraphs),
                'format': 'Word'
            }

            print(f"✅ Đã đọc Word: {Path(file_path).name}")

            return {
                'content': content.strip(),
                'metadata': metadata
            }

        except Exception as e:
            print(f"❌ Lỗi đọc Word {file_path}: {e}")
            return {'content': '', 'metadata': {'error': str(e)}}

    def load_text(self, file_path: str) -> Dict:
        """
        Đọc file text (.txt, .md)

        Args:
            file_path: Đường dẫn file text

        Returns:
            Dict: {'content': str, 'metadata': dict}
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata = {
                'source': Path(file_path).name,
                'file_path': str(file_path),
                'type': Path(file_path).suffix[1:],
                'format': 'Text'
            }

            print(f"✅ Đã đọc text: {Path(file_path).name}")

            return {
                'content': content.strip(),
                'metadata': metadata
            }

        except Exception as e:
            print(f"❌ Lỗi đọc text {file_path}: {e}")
            return {'content': '', 'metadata': {'error': str(e)}}

    def load_file(self, file_path: str) -> Dict:
        """
        Đọc file tự động dựa trên extension

        Args:
            file_path: Đường dẫn file

        Returns:
            Dict: {'content': str, 'metadata': dict}
        """
        file_path = Path(file_path)

        if not file_path.exists():
            print(f"❌ File không tồn tại: {file_path}")
            return {'content': '', 'metadata': {'error': 'File not found'}}

        extension = file_path.suffix.lower()

        if extension == '.pdf':
            return self.load_pdf(str(file_path))
        elif extension in ['.docx', '.doc']:
            return self.load_docx(str(file_path))
        elif extension in ['.txt', '.md']:
            return self.load_text(str(file_path))
        else:
            print(f"❌ Không hỗ trợ định dạng: {extension}")
            return {'content': '', 'metadata': {'error': f'Unsupported format: {extension}'}}

    def load_directory(
        self,
        directory: str,
        recursive: bool = True
    ) -> List[Dict]:
        """
        Đọc tất cả file trong thư mục

        Args:
            directory: Đường dẫn thư mục
            recursive: Có đọc thư mục con hay không

        Returns:
            List[Dict]: Danh sách documents
        """
        directory = Path(directory)

        if not directory.exists():
            print(f"❌ Thư mục không tồn tại: {directory}")
            return []

        documents = []

        # Pattern để tìm file
        pattern = "**/*" if recursive else "*"

        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                doc = self.load_file(str(file_path))
                if doc['content']:  # Chỉ thêm nếu có content
                    documents.append(doc)

        print("\n📚 Tổng kết:")
        print(f"  - Đã đọc {len(documents)} files từ {directory}")

        return documents


def demo_document_loader():
    """Demo chức năng document loader"""
    print("=" * 60)
    print("DEMO - DOCUMENT LOADER")
    print("=" * 60)

    # Tạo loader
    loader = DocumentLoader()

    # Tạo file text mẫu để demo
    print("\n1️⃣  Tạo file mẫu...")

    sample_dir = config.HEALTH_KNOWLEDGE_DIR
    sample_dir.mkdir(parents=True, exist_ok=True)

    # Tạo file text mẫu
    sample_text = """
HƯỚNG DẪN CHĂM SÓC SỨC KHỎE CƠ BẢN

1. PHÒNG NGỪA CẢM CÚM

Cảm cúm là bệnh nhiễm virus phổ biến, đặc biệt vào mùa đông.

Triệu chứng:
- Sốt cao (38-40°C)
- Đau đầu và đau cơ
- Ho, đau họng
- Mệt mỏi

Cách phòng ngừa:
1. Rửa tay thường xuyên bằng xà phòng
2. Đeo khẩu trang nơi đông người
3. Tăng cường vitamin C
4. Tiêm vaccine phòng cúm hàng năm

2. XỬ LÝ ĐAU ĐẦU

Đau đầu có nhiều nguyên nhân:
- Căng thẳng, stress
- Mất ngủ
- Thiếu nước
- Nhìn màn hình máy tính lâu

Cách giảm đau:
- Nghỉ ngơi trong phòng tối, yên tĩnh
- Massage nhẹ vùng thái dương
- Uống đủ nước (2 lít/ngày)
- Chườm lạnh hoặc ấm lên vùng đau

⚠️ KHI NÀO CẦN ĐI KHÁM:
- Đau đầu dữ dội đột ngột
- Đau đầu kèm sốt cao, nôn
- Đau đầu kéo dài >3 ngày

3. CHĂM SÓC SỨC KHỎE TINH THẦN

Stress và lo âu ảnh hưởng đến sức khỏe:

Dấu hiệu cần chú ý:
- Mất ngủ kéo dài
- Mệt mỏi thường xuyên
- Giảm hứng thú với mọi việc
- Khó tập trung

Cách cải thiện:
1. Tập thể dục đều đặn
2. Thiền, yoga
3. Dành thời gian cho sở thích
4. Nói chuyện với người thân
5. Tìm tư vấn tâm lý chuyên nghiệp nếu cần

---
Nguồn: Bộ Y Tế - Hướng dẫn chăm sóc sức khỏe cộng đồng
Cập nhật: 2026
"""

    sample_file = sample_dir / "health_guide_sample.txt"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_text)

    print(f"✅ Đã tạo file: {sample_file.name}")

    # Test load file đơn
    print("\n2️⃣  TEST LOAD FILE ĐƠN")
    print("=" * 60)

    doc = loader.load_file(str(sample_file))

    print("\n📄 Document info:")
    print(f"  Source: {doc['metadata']['source']}")
    print(f"  Type: {doc['metadata']['type']}")
    print(f"  Content length: {len(doc['content'])} ký tự")
    print("\n📝 Nội dung (200 ký tự đầu):")
    print(f"  {doc['content'][:200]}...")

    # Test load directory
    print("\n3️⃣  TEST LOAD DIRECTORY")
    print("=" * 60)

    documents = loader.load_directory(str(sample_dir))

    print("\n📚 Kết quả:")
    for i, doc in enumerate(documents, 1):
        print(f"\n  Document {i}:")
        print(f"    File: {doc['metadata']['source']}")
        print(f"    Type: {doc['metadata']['format']}")
        print(f"    Size: {len(doc['content'])} ký tự")

    print("\n✅ Demo hoàn tất!")
    print("\n💡 Hướng dẫn sử dụng:")
    print(f"  1. Đưa file PDF/Word vào thư mục: {sample_dir}")
    print(f"  2. Chạy loader.load_directory('{sample_dir}')")
    print("  3. Documents sẽ được đọc tự động!")


if __name__ == "__main__":
    demo_document_loader()
