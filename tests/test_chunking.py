from backend.utils.chunking import SectionBasedChunker


def test_section_based_chunker_basic():
    """Kiểm tra chức năng chia chunk theo section cơ bản"""
    chunker = SectionBasedChunker()

    text = """
Tiêu đề: Bệnh Cảm Cúm
    
1. Tổng quan
Cảm cúm là một bệnh truyền nhiễm hô hấp cấp tính.
    
2. Dấu hiệu thường gặp
Bao gồm sốt, ho, đau họng, đau cơ.
    
3. Nguyên nhân phổ biến
Do virus cúm gây ra.
"""

    chunks = chunker.chunk_by_sections(
        text, metadata={"source": "cam_cum.txt"})

    assert len(chunks) == 3
    # Nên có chunk cho phần 'Tổng quan', 'Dấu hiệu', 'Nguyên nhân'

    # Kiểm tra metadata được thêm vào đúng
    chunk_titles = [chunk['metadata'].get(
        'section_title') for chunk in chunks if 'section_title' in chunk['metadata']]
    assert 'Tổng quan' in chunk_titles
    assert 'Dấu hiệu thường gặp' in chunk_titles
    assert 'Nguyên nhân phổ biến' in chunk_titles


def test_extract_title():
    """Kiểm tra khả năng lấy tiêu đề từ văn bản"""
    chunker = SectionBasedChunker()
    text = "Tiêu đề: Bệnh Béo Phì\nNguồn: WHO\n\n1. Tổng quan\nBéo phì là..."

    title = chunker.extract_title(text)

    assert title == 'Bệnh Béo Phì'
