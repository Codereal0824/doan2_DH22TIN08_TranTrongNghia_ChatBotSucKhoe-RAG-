"""
Rebuild Vector Database with Section-Based Chunking
This script backs up old database and rebuilds with new chunking method
"""
from pathlib import Path
import shutil
from datetime import datetime


def backup_current_database():
    """Backup current vector database"""
    vector_store_dir = Path("data/vector_store")

    if not vector_store_dir.exists():
        print("⚠️  No existing vector store to backup")
        return

    # Create backup directory
    backup_dir = Path("data/vector_store_backup")
    backup_dir.mkdir(exist_ok=True)

    # Create timestamped backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"vector_store_backup_{timestamp}"
    backup_path = backup_dir / backup_name

    # Copy vector store files
    print(f"\n📦 Backing up current vector database...")
    print(f"   Source: {vector_store_dir}")
    print(f"   Destination: {backup_path}")

    try:
        shutil.copytree(vector_store_dir, backup_path)
        print(f"✅ Backup created successfully!")

        # Show backup files
        backup_files = list(backup_path.glob("*"))
        print(f"\n📂 Backup contains {len(backup_files)} files:")
        for file in backup_files:
            size_kb = file.stat().st_size / 1024
            print(f"   - {file.name} ({size_kb:.1f} KB)")

        return backup_path
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None


def rebuild_database():
    """Rebuild vector database with section-based chunking"""
    print("\n" + "=" * 80)
    print("🔄 REBUILDING VECTOR DATABASE WITH SECTION-BASED CHUNKING")
    print("=" * 80)

    # Import build script
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from scripts.build_vector_db import build_vector_database

    # Build database
    success = build_vector_database()

    return success


def main():
    """Main function"""
    print("=" * 80)
    print("VECTOR DATABASE REBUILD TOOL")
    print("=" * 80)

    print("\n⚠️  This will rebuild the vector database using Section-Based Chunking")
    print("   Your current database will be backed up first.")
    print("\nBenefits of Section-Based Chunking:")
    print("   ✅ Each section becomes a complete semantic unit")
    print("   ✅ Better retrieval accuracy (matches by section meaning)")
    print("   ✅ Preserves document structure (Title + Section + Content)")

    # Ask for confirmation
    print("\n" + "─" * 80)
    response = input("Continue? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print("\n❌ Rebuild cancelled")
        return

    # Step 1: Backup
    print("\n" + "=" * 80)
    print("STEP 1: BACKUP CURRENT DATABASE")
    print("=" * 80)
    backup_path = backup_current_database()

    if backup_path:
        print(f"\n✅ Backup completed: {backup_path}")

    # Step 2: Rebuild
    print("\n" + "=" * 80)
    print("STEP 2: REBUILD WITH SECTION-BASED CHUNKING")
    print("=" * 80)

    success = rebuild_database()

    if success:
        print("\n" + "=" * 80)
        print("✅ REBUILD COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print("\nYour vector database now uses Section-Based Chunking")
        print("The retriever will match queries to semantic sections")

        if backup_path:
            print(f"\n💾 Old database backed up to: {backup_path}")
            print("   You can restore it if needed by copying files back")
    else:
        print("\n" + "=" * 80)
        print("❌ REBUILD FAILED!")
        print("=" * 80)

        if backup_path:
            print(f"\n💾 Your original database is safe at: {backup_path}")
            print("   You can restore it manually if needed")


if __name__ == "__main__":
    main()
