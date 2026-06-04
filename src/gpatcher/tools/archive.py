import os
import zipfile

def compress_dir(src_dir: str, zip_out: str):
    """Zips the contents of src_dir into zip_out using ZIP_DEFLATED."""
    if os.path.exists(zip_out):
        os.remove(zip_out)
    with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(src_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, src_dir)
                zipf.write(full_path, rel_path)

def expand_dir(zip_path: str, dest_dir: str):
    """Extracts all contents of zip_path to dest_dir."""
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zipf:
        zipf.extractall(dest_dir)
