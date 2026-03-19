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
