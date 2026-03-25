"""
Validate content quality after crawling
"""
from pathlib import Path
import re

# Hàm đánh giá chất lượng của từng tài liệu văn bản (Data Quality Assurance).
# Sử dụng các quy tắc kinh nghiệm (Heuristic Rules) để phát hiện dữ liệu rác (Noise)
# hoặc dữ liệu bị lỗi trong quá trình thu thập (Web Scraping / Data Ingestion).


def validate_file(filepath):
    """Kiểm tra chất lượng file"""
    issues = []

    # Đọc tệp tin với bộ mã hóa UTF-8 để hỗ trợ tiếng Việt
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Kiểm tra giới hạn dưới của dữ liệu (Minimum Length Threshold).
    # Văn bản quá ngắn thường là dữ liệu không có giá trị thông tin (Insufficient Information).
    if len(content) < 200:
        issues.append("[CANH BAO] Noi dung qua ngan (< 200 ky tu)")

    # 2. Kiểm tra tính toàn vẹn của cấu trúc Siêu dữ liệu (Metadata Structure Integrity).
    # Đảm bảo hệ thống Chunking sau này có thể trích xuất được Tiêu đề để nạp vào FAISS.
    if not content.startswith("Tiêu đề:"):
        issues.append("[CANH BAO] Thieu tieu de")

    # 3. Kiểm tra tính minh bạch của tài liệu (Source Grounding Check).
    if "Nguồn:" not in content:
        issues.append("[CANH BAO] Thieu nguon")

    # 4. Quét mã lỗi HTTP thường gặp khi thu thập dữ liệu tự động (Scraping Error Detection).
    error_keywords = [
        "page not found",
        "404",
        "access denied",
        "please try again",
        "content not available"
    ]

    content_lower = content.lower()
    for keyword in error_keywords:
        if keyword in content_lower:
            issues.append(f"[LOI] Phat hien ma loi thu thap: '{keyword}'")

    # 5. Phân tích Tần suất Ký tự bất thường (Anomaly Character Detection).
    # Sử dụng Biểu thức chính quy (Regex) để phát hiện lỗi mã hóa (Encoding issues)
    # hoặc mã HTML rác còn sót lại chưa được làm sạch.
    weird_chars = re.findall(
        r'[^\w\s\.,;:?!\-\(\)\[\]\'"\/\nđĐàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ%€]', content)
    if len(weird_chars) > 50:
        issues.append(
            f"[CANH BAO] Nhieu ky tu la (Regex Filter): {len(weird_chars)}")

    # 6. Xác minh Miền tri thức (Domain Verification).
    # Đếm tần suất xuất hiện của các Thuật ngữ Y khoa cốt lõi. Nếu quá thấp,
    # tài liệu này có nguy cơ cao đã bị phân loại nhầm chủ đề (Out-of-domain data).
    health_keywords = [
        'triệu chứng', 'bệnh', 'điều trị', 'phòng ngừa',
        'sức khỏe', 'chẩn đoán', 'thuốc', 'bác sĩ'
    ]

    found_keywords = sum(1 for kw in health_keywords if kw in content_lower)
    if found_keywords < 2:
        issues.append(
            f"[CANH BAO] It tu khoa y te, nguy co sai chu de ({found_keywords}/8)")

    return issues


# Hàm thực thi kiểm thử hàng loạt (Batch Validation Pipeline)
def validate_all():
    """Validate tất cả files"""
    data_dir = Path("data/health_knowledge")

    # Quét toàn bộ thư mục để lấy danh sách các tệp tin văn bản thuần
    files = list(data_dir.glob("*.txt"))

    print("=" * 70)
    print(f"[KIEM DINH] DANH GIA CHAT LUONG {len(files)} FILES DU LIEU")
    print("=" * 70)

    total_issues = 0
    problematic_files = []

    for filepath in sorted(files):
        issues = validate_file(filepath)

        if issues:
            total_issues += len(issues)
            problematic_files.append(filepath.name)

            print(f"\n[FILE] {filepath.name}")
            for issue in issues:
                print(f"   {issue}")
        else:
            print(f"[HOP LE] {filepath.name}")

    print("\n" + "=" * 70)
    print("[THONG KE] TONG KET CHAT LUONG DATASET:")
    print(f"   - Tong files: {len(files)}")
    print(f"   - Files HOP LE (Clean): {len(files) - len(problematic_files)}")
    print(f"   - Files CO VAN DE (Noisy): {len(problematic_files)}")
    print(f"   - Tong so Canh bao/Loi: {total_issues}")

    if problematic_files:
        print("\n[DANH SACH] CAN KIEM TRA THU CONG (MANUAL REVIEW):")
        for fname in problematic_files:
            print(f"   - {fname}")

    print("=" * 70)


if __name__ == "__main__":
    validate_all()
