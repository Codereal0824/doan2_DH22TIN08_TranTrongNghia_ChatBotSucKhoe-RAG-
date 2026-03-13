import os

# ==========================================
# CẤU HÌNH
# ==========================================
# Các thư mục cần BỎ QUA (Rất quan trọng để tránh file quá nặng)
IGNORE_DIRS = {
    'venv', '__pycache__', '.git', '.vscode', 'node_modules',
    'vector_store', 'health_knowledge'  # Bỏ qua data vì nó quá dài
}

# Các loại file muốn lấy code
ALLOWED_EXTENSIONS = {'.py', '.md', '.txt', '.env.example', '.json', '.yml'}

# Tên file đầu ra
OUTPUT_FILE = 'FULL_PROJECT_CONTEXT.txt'


def export_project():
    root_dir = os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))  # Lấy thư mục gốc dự án
    output_path = os.path.join(root_dir, OUTPUT_FILE)

    with open(output_path, 'w', encoding='utf-8') as outfile:
        # Ghi cấu trúc thư mục (Tree structure)
        outfile.write("=== PROJECT STRUCTURE ===\n")
        for root, dirs, files in os.walk(root_dir):
            # Lọc bỏ thư mục rác
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            level = root.replace(root_dir, '').count(os.sep)
            indent = ' ' * 4 * (level)
            outfile.write(f"{indent}{os.path.basename(root)}/\n")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                outfile.write(f"{subindent}{f}\n")

        outfile.write("\n" + "="*50 + "\n\n")

        # Ghi nội dung từng file
        print(f"[-] Đang quét file từ: {root_dir}")
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                file_ext = os.path.splitext(file)[1]
                if file_ext in ALLOWED_EXTENSIONS and file != OUTPUT_FILE:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, root_dir)

                    # Bỏ qua file .env thật để lộ API Key (Chỉ lấy .env.example nếu có)
                    if file == '.env':
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()

                        outfile.write(f"START_FILE: {rel_path}\n")
                        outfile.write("-" * 20 + "\n")
                        outfile.write(content)
                        outfile.write("\n" + "-" * 20 + "\n")
                        outfile.write(f"END_FILE: {rel_path}\n\n")
                        print(f"   + Đã thêm: {rel_path}")
                    except Exception as e:
                        print(f"   [!] Lỗi đọc file {rel_path}: {e}")

    print(f"\n[SUCCESS] Đã xuất toàn bộ dự án ra file: {OUTPUT_FILE}")
    print("Bạn hãy upload file này lên khung chat cho AI nhé!")


if __name__ == "__main__":
    export_project()
