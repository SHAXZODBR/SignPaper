# Compress large PDFs
import os
import fitz # PyMuPDF
from pathlib import Path

def compress_pdf(input_path, output_path):
    print(f"Compressing {input_path}...")
    try:
        doc = fitz.open(input_path)
        # Save with garbage collection and compression
        doc.save(output_path, garbage=4, deflate=True, clean=True)
        doc.close()
        
        old_size = os.path.getsize(input_path) / (1024 * 1024)
        new_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  Done: {old_size:.1f}MB -> {new_size:.1f}MB")
        return new_size
    except Exception as e:
        print(f"  Error: {e}")
        return None

# Target files
large_files = [
    r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books\uzbek\Tarix\6-sinf Tarix yangi darslik..pdf",
    r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books\uzbek\Biologiya\botanika_6_uzb.pdf"
]

Path("temp_compressed").mkdir(exist_ok=True)

for f in large_files:
    if os.path.exists(f):
        out_name = "compressed_" + os.path.basename(f)
        out_path = os.path.join("temp_compressed", out_name)
        compress_pdf(f, out_path)
    else:
        print(f"File not found: {f}")
