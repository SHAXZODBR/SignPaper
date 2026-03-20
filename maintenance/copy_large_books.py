# Copy large files safely
import shutil
import os
from pathlib import Path

BASE_DIR = r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books"
TARGET_DIR = Path("assets/large_books")
TARGET_DIR.mkdir(parents=True, exist_ok=True)

files_to_copy = [
    (r"uzbek\Tarix\6-sinf Tarix yangi darslik..pdf", "6-sinf_tarix.pdf"),
    (r"uzbek\Biologiya\botanika_6_uzb.pdf", "botanika_6_uzb.pdf"),
    (r"uzbek\Tarix\8_sinf_Jahon_tarixi.pdf", "8-sinf_jahon_tarixi.pdf")
]

for src_rel, dst_name in files_to_copy:
    src_path = Path(BASE_DIR) / src_rel
    dst_path = TARGET_DIR / dst_name
    
    if src_path.exists():
        print(f"Copying {src_path} -> {dst_path}...")
        shutil.copy2(src_path, dst_path)
        print(f"  Done. Size: {os.path.getsize(dst_path)/(1024*1024):.1f}MB")
    else:
        print(f"Skipping {src_path} (does not exist)")
