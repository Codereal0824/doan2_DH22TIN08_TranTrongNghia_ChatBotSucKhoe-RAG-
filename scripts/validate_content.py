"""
Validate content quality after crawling
"""
from pathlib import Path
import re


def validate_file(filepath):
    """Kiểm tra chất lượng file"""
    issues = []

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Độ dài tối thiểu
    if len(content) < 200:
        issues.append("⚠️ Nội dung quá ngắn (< 200 ký tự)")

    # 2. Kiểm tra có tiêu đề
    if not content.startswith("Tiêu đề:"):
        issues.append("⚠️ Thiếu tiêu đề")

    # 3. Kiểm tra có nguồn
    if "Nguồn:" not in content:
        issues.append("⚠️ Thiếu nguồn")

    # 4. Nội dung bị lỗi
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
            issues.append(f"❌ Phát hiện lỗi: '{keyword}'")

    # 5. Quá nhiều ký tự lạ
    weird_chars = re.findall(
        r'[^\w\s\.,;:?!\-\(\)\[\]\'"\/\nđĐàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ%€]', content)
    if len(weird_chars) > 50:
        issues.append(f"⚠️ Nhiều ký tự lạ: {len(weird_chars)}")

    # 6. Nội dung y tế hợp lệ
    health_keywords = [
        'triệu chứng', 'bệnh', 'điều trị', 'phòng ngừa',
        'sức khỏe', 'chẩn đoán', 'thuốc', 'bác sĩ'
    ]

    found_keywords = sum(1 for kw in health_keywords if kw in content_lower)
    if found_keywords < 2:
        issues.append(f"⚠️ Ít từ khóa y tế ({found_keywords}/8)")

    return issues


def validate_all():
    """Validate tất cả files"""
    data_dir = Path("data/health_knowledge")
    files = list(data_dir.glob("*.txt"))

    print("=" * 70)
    print(f"🔍 KIỂM TRA CHẤT LƯỢNG {len(files)} FILES")
    print("=" * 70)

    total_issues = 0
    problematic_files = []

    for filepath in sorted(files):
        issues = validate_file(filepath)

        if issues:
            total_issues += len(issues)
            problematic_files.append(filepath.name)

            print(f"\n📄 {filepath.name}")
            for issue in issues:
                print(f"   {issue}")
        else:
            print(f"✅ {filepath.name}")

    print("\n" + "=" * 70)
    print(f"📊 TỔNG KẾT:")
    print(f"   - Tổng files: {len(files)}")
    print(f"   - Files OK: {len(files) - len(problematic_files)}")
    print(f"   - Files có vấn đề: {len(problematic_files)}")
    print(f"   - Tổng issues: {total_issues}")

    if problematic_files:
        print(f"\n⚠️ CẦN KIỂM TRA:")
        for fname in problematic_files:
            print(f"   - {fname}")

    print("=" * 70)


if __name__ == "__main__":
    validate_all()
