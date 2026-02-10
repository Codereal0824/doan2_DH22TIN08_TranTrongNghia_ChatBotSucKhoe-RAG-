"""
Script tự động thêm tài khoản mẫu vào database
Sử dụng: python create_sample_users.py
"""
from backend.auth.auth_service import AuthService
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))


def create_sample_users():
    """Tạo các tài khoản mẫu"""
    print("=" * 70)
    print("👥 TẠO TÀI KHOẢN MẪU")
    print("=" * 70)

    auth = AuthService()

    # Danh sách tài khoản mẫu
    sample_users = [
        {
            'username': 'testuser',
            'email': 'test@gmail.com',
            'password': '123456',
            'confirm_password': '123456'
        },
        {
            'username': 'nguyenvana',
            'email': 'nguyenvana@gmail.com',
            'password': '123456',
            'confirm_password': '123456'
        },
        {
            'username': 'user1',
            'email': 'user1@example.com',
            'password': '123456',
            'confirm_password': '123456'
        }
    ]

    created_count = 0
    skipped_count = 0

    for user_data in sample_users:
        print(f"\n📝 Đang tạo user: {user_data['username']}")
        print("-" * 70)

        success, message, user_id = auth.register_user(
            username=user_data['username'],
            email=user_data['email'],
            password=user_data['password'],
            confirm_password=user_data['confirm_password']
        )

        if success:
            print(f"✅ {message}")
            print(f"   User ID: {user_id}")
            print(f"   Email: {user_data['email']}")
            print(f"   Password: {user_data['password']}")
            created_count += 1
        else:
            print(f"⚠️  {message}")
            skipped_count += 1

    # Summary
    print("\n" + "=" * 70)
    print("📊 KẾT QUẢ")
    print("=" * 70)
    print(f"✅ Đã tạo: {created_count} tài khoản")
    print(f"⚠️  Bỏ qua: {skipped_count} tài khoản (đã tồn tại)")

    if created_count > 0:
        print("\n🎉 Tài khoản mẫu đã sẵn sàng!")
        print("\n📋 DANH SÁCH TÀI KHOẢN:")
        print("-" * 70)
        for user in sample_users:
            print(
                f"Username: {user['username']:15} | Password: {user['password']}")
        print("-" * 70)
        print("\n💡 Bạn có thể đăng nhập tại: http://localhost:5000/login")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    try:
        create_sample_users()
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
