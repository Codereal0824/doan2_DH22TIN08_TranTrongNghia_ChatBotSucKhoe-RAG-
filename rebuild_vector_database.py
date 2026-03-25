"""
Rebuild Vector Database with Section-Based Chunking
This script backs up old database and rebuilds with new chunking method
"""
from pathlib import Path
import shutil
from datetime import datetime

# ============================================
# CƠ CHẾ PHỤC HỒI SAU THẢM HỌA (DISASTER RECOVERY)
# ============================================

# Hàm này thực thi nguyên tắc an toàn dữ liệu tối thượng trong DevOps.
# Trước khi thực hiện bất kỳ thao tác mang tính phá hủy (Destructive Operation)
# nào lên Cơ sở dữ liệu hiện tại (như Rebuild/Overwrite Index), hệ thống BẮT BUỘC
# phải tạo ra một bản sao lưu (Snapshot/Backup) để có thể hoàn tác (Rollback) nếu xảy ra lỗi.


def backup_current_database():
    """Backup current vector database"""
    vector_store_dir = Path("data/vector_store")

    if not vector_store_dir.exists():
        print("[CANH BAO] Khong co vector store hien tai de backup")
        return

    # Tự động tạo thư mục lưu trữ dự phòng
    backup_dir = Path("data/vector_store_backup")
    backup_dir.mkdir(exist_ok=True)

    # Kỹ thuật Timestamping: Gắn nhãn thời gian thực vào tên thư mục backup.
    # Đảm bảo các bản sao lưu không bị ghi đè lẫn nhau theo thời gian (Versioning).
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"vector_store_backup_{timestamp}"
    backup_path = backup_dir / backup_name

    print("\n[TIEN TRINH] Backing up current vector database...")
    print(f"   Source: {vector_store_dir}")
    print(f"   Destination: {backup_path}")

    try:
        # Sao chép đệ quy toàn bộ cây thư mục (bao gồm cả file .faiss và .pkl)
        shutil.copytree(vector_store_dir, backup_path)
        print("[THANH CONG] Tao backup thanh cong!")

        # Đo lường và báo cáo dung lượng để kiểm soát tài nguyên đĩa cứng
        backup_files = list(backup_path.glob("*"))
        print(f"\n[THONG TIN] Backup bao gom {len(backup_files)} files:")
        for file in backup_files:
            size_kb = file.stat().st_size / 1024
            print(f"   - {file.name} ({size_kb:.1f} KB)")

        return backup_path
    except Exception as e:
        print(f"[LOI] Backup failed: {e}")
        return None

# Hàm Trình bao bọc (Wrapper) dùng để kích hoạt lại luồng ETL Pipeline
# từ script build_vector_db.py đã viết trước đó.


def rebuild_database():
    """Rebuild vector database with section-based chunking"""
    print("\n" + "=" * 80)
    print("[TIEN TRINH] REBUILDING VECTOR DATABASE WITH SECTION-BASED CHUNKING")
    print("=" * 80)

    # Can thiệp đường dẫn hệ thống để gọi Script anh em (Sibling Script)
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from scripts.build_vector_db import build_vector_database

    # Kích hoạt tiến trình Build
    success = build_vector_database()

    return success


def main():
    """Main function"""
    print("=" * 80)
    print("VECTOR DATABASE REBUILD TOOL")
    print("=" * 80)

    print("\n[CANH BAO] Cong cu nay se tao lai Vector Database dung Section-Based Chunking.")
    print("   Database hien tai cua ban se duoc backup truoc tien.")
    print("\n[THONG TIN] Loi ich cua Section-Based Chunking (Chia nho theo Ngu nghia):")
    print(
        "   [+] Moi section tro thanh mot don vi ngu nghia hoan chinh (Semantic Unit)")
    print("   [+] Do chinh xac truy xuat cao hon do khop nguyen mang y nghia")
    print("   [+] Bao toan cau truc tai lieu goc (Title + Section + Content)")

    # ============================================
    # BẢO VỆ TƯƠNG TÁC (INTERACTIVE SAFEGUARD)
    # ============================================
    # Cơ chế xác nhận thủ công (Prompt Confirmation) chống lại việc
    # vô tình chạy Script làm gián đoạn dịch vụ đang chạy trực tuyến (Production).
    print("\n" + "-" * 80)
    response = input("Ban co muon tiep tuc? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n[DA HUY] Qua trinh Rebuild da bi huy bo")
        return

    # Bước 1: Sao lưu
    print("\n" + "=" * 80)
    print("STEP 1: BACKUP CURRENT DATABASE")
    print("=" * 80)
    backup_path = backup_current_database()

    if backup_path:
        print(f"\n[THANH CONG] Backup hoan tat tai: {backup_path}")

    # Bước 2: Tái thiết lập
    print("\n" + "=" * 80)
    print("STEP 2: REBUILD WITH SECTION-BASED CHUNKING")
    print("=" * 80)

    success = rebuild_database()

    if success:
        print("\n" + "=" * 80)
        print("[THANH CONG] REBUILD COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nVector Database cua ban hien da dung Section-Based Chunking.")
        print("He thong Retriever se khop cau hoi theo tung phan ngu nghia (Semantic Sections).")

        if backup_path:
            print(
                f"\n[THONG TIN] Database cu duoc luu tru an toan tai: {backup_path}")
            print(
                "   Ban co the khoi phuc lai (Restore) bang cach copy file nguoc tro lai.")
    else:
        print("\n" + "=" * 80)
        print("[LOI] REBUILD FAILED!")
        print("=" * 80)

        if backup_path:
            print(
                f"\n[THONG TIN] Database goc cua ban van an toan tai: {backup_path}")
            print("   Ban co the khoi phuc thu cong neu can thiet.")


if __name__ == "__main__":
    main()
