"""
Verify clean extraction and installation of AUGIS_FINAL_COMPLETE.zip
"""
import os
import zipfile
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZIP_PATH = os.path.join(BASE_DIR, "AUGIS_FINAL_COMPLETE.zip")
EXTRACT_DIR = os.path.join(BASE_DIR, "scratch_delivery_test")

def test_extraction():
    print(f"Testing extraction of: {ZIP_PATH}")
    if os.path.exists(EXTRACT_DIR):
        shutil.rmtree(EXTRACT_DIR, ignore_errors=True)

    with zipfile.ZipFile(ZIP_PATH, 'r') as zipf:
        zipf.extractall(EXTRACT_DIR)

    extracted_files = [os.path.join(r, f) for r, d, fs in os.walk(EXTRACT_DIR) for f in fs]
    print(f"[OK] Successfully extracted {len(extracted_files)} files into {EXTRACT_DIR}")

    # Run manage.py check inside extracted directory
    py_exec = sys.executable
    print(f"Running system check on extracted project using: {py_exec}...")
    res = subprocess.run(
        [py_exec, "manage.py", "check"],
        cwd=EXTRACT_DIR,
        capture_output=True,
        text=True
    )
    print("Return code:", res.returncode)
    print("Stdout:", res.stdout.strip())
    print("Stderr:", res.stderr.strip())

    assert res.returncode == 0, f"manage.py check failed inside extracted archive: {res.stderr}"
    print("[OK] System check passed with 0 issues inside extracted directory!")

    # Clean up
    shutil.rmtree(EXTRACT_DIR, ignore_errors=True)
    print("[OK] Cleaned up temporary test directory.")

if __name__ == "__main__":
    test_extraction()
