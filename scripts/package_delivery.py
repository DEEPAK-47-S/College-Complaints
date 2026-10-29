"""
AUGIS Final Delivery Package Builder
Packages AUGIS_FINAL_COMPLETE.zip excluding venv, caches, git, and sensitive private files.
"""
import os
import zipfile
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_ZIP = os.path.join(BASE_DIR, "AUGIS_FINAL_COMPLETE.zip")

EXCLUDE_DIRS = {
    '.venv', 'venv', 'env', '.git', '.github', '.pytest_cache', '__pycache__',
    '.idea', '.vscode', '.system_generated', 'node_modules', '.kilo', '.gemini'
}

EXCLUDE_EXTENSIONS = {
    '.pyc', '.pyo', '.pyd', '.log', '.tmp', '.swp'
}

EXCLUDE_FILES = {
    'AUGIS_FINAL_COMPLETE.zip', '.DS_Store', 'Thumbs.db', 'dashboard_dump.txt'
}

def should_exclude(rel_path):
    parts = rel_path.replace('\\', '/').split('/')
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    
    fname = parts[-1]
    if fname in EXCLUDE_FILES:
        return True
    
    _, ext = os.path.splitext(fname)
    if ext in EXCLUDE_EXTENSIONS:
        return True
    
    # Exclude uploaded media documents, but keep directory structure
    if 'media/documents' in rel_path.replace('\\', '/') and fname not in {'.gitkeep', 'README.md'}:
        return True

    return False

def build_zip():
    print(f"Building delivery package: {OUTPUT_ZIP}")
    if os.path.exists(OUTPUT_ZIP):
        os.remove(OUTPUT_ZIP)

    file_count = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(OUTPUT_ZIP, 'w', compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(BASE_DIR):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, BASE_DIR)

                if should_exclude(rel_path):
                    continue

                zipf.write(abs_path, rel_path)
                file_count += 1
                total_uncompressed_bytes += os.path.getsize(abs_path)

    zip_size_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"[OK] Package built successfully!")
    print(f"  Files packaged: {file_count}")
    print(f"  Uncompressed size: {total_uncompressed_bytes / (1024 * 1024):.2f} MB")
    print(f"  ZIP file size: {zip_size_mb:.2f} MB")
    print(f"  Location: {OUTPUT_ZIP}")

def verify_zip():
    print(f"\nVerifying ZIP integrity: {OUTPUT_ZIP}")
    with zipfile.ZipFile(OUTPUT_ZIP, 'r') as zipf:
        bad_file = zipf.testzip()
        if bad_file:
            print(f"[ERROR] Corrupt file detected in ZIP: {bad_file}")
            sys.exit(1)
        namelist = zipf.namelist()
        print(f"[OK] CRC32 Check Passed! Total archive entries: {len(namelist)}")
        
        # Verify critical files presence
        critical_files = [
            'manage.py',
            'start.bat',
            'vercel.json',
            'wsgi_vercel.py',
            'build_files.sh',
            'requirements.txt',
            'config/settings/base.py',
            'config/settings/development.py',
            'config/settings/production.py',
            'apps/accounts/models.py',
            'apps/complaints/models.py',
            'apps/intelligence/models.py',
            'apps/intelligence/gemini_service.py',
            'apps/reports/services.py',
            'templates/accounts/verify_otp.html',
            'templates/dashboard/index.html',
            'templates/reports/index.html',
            'templates/institutions/institution_360.html',
            'templates/intelligence/candidate_detail.html',
            'scripts/seed_tamil_nadu_colleges.py',
            'scripts/playwright_smoke_test.py'
        ]
        for cf in critical_files:
            match = any(cf == name.replace('\\', '/') for name in namelist)
            assert match, f"Critical file missing in archive: {cf}"
            print(f"  [OK] Verified present: {cf}")

    print("\nAll ZIP validation checks passed successfully!")

if __name__ == "__main__":
    build_zip()
    verify_zip()
