import os
import sys
import json
import urllib.request
import tempfile
import zipfile
import shutil
import re
from gpatcher.core.common import get_app_data_dir, get_bin_path, log_info, log_ok

def fetch_hdiffpatch():
    """Queries, downloads, and extracts the correct HDiffPatch binaries for the current OS."""
    url = 'https://api.github.com/repos/sisong/HDiffPatch/releases/latest'
    req = urllib.request.Request(url, headers={'User-Agent': 'gpatcher-fetch'})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        raise RuntimeError(f"Failed to query latest HDiffPatch release from GitHub: {e}")

    tag = data.get('tag_name', 'latest')
    assets = data.get('assets', [])

    is_win = sys.platform == 'win32'
    is_mac = sys.platform == 'darwin'

    if is_win:
        pattern = r'win.*64'
    elif is_mac:
        pattern = r'osx.*64|macos'
    else:
        pattern = r'linux.*64'

    selected_asset = None
    for asset in assets:
        name = asset.get('name', '')
        if re.search(pattern, name, re.IGNORECASE) and name.endswith('.zip'):
            selected_asset = asset
            break

    # Fallbacks
    if not selected_asset:
        for asset in assets:
            name = asset.get('name', '')
            if name.endswith('.zip'):
                if is_win and 'win' in name.lower():
                    selected_asset = asset
                    break
                elif is_mac and ('osx' in name.lower() or 'mac' in name.lower()):
                    selected_asset = asset
                    break
                elif not is_win and not is_mac and 'linux' in name.lower():
                    selected_asset = asset
                    break

    if not selected_asset:
        raise RuntimeError(f"No zip asset found in HDiffPatch {tag} matching current platform pattern '{pattern}'")

    asset_name = selected_asset['name']
    download_url = selected_asset['browser_download_url']

    log_info(f"HDiffPatch Release: {tag}")
    log_info(f"Downloading: {asset_name} ({format_bytes_count(selected_asset['size'])})...")

    temp_dir = tempfile.mkdtemp(prefix='hdp-')
    zip_path = os.path.join(temp_dir, 'hdp.zip')
    try:
        urllib.request.urlretrieve(download_url, zip_path)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)

        # Walk temp_dir to find hdiffz and hpatchz
        bin_ext = '.exe' if is_win else ''
        hdiffz_name = f"hdiffz{bin_ext}"
        hpatchz_name = f"hpatchz{bin_ext}"

        hdiffz_src = None
        hpatchz_src = None

        for root, _, files in os.walk(temp_dir):
            for file in files:
                if file.lower() == hdiffz_name.lower():
                    hdiffz_src = os.path.join(root, file)
                elif file.lower() == hpatchz_name.lower():
                    hpatchz_src = os.path.join(root, file)

        if not hdiffz_src or not hpatchz_src:
            raise RuntimeError(f"Could not find {hdiffz_name} or {hpatchz_name} inside extracted zip.")

        bin_dir = os.path.join(get_app_data_dir(), 'bin')
        os.makedirs(bin_dir, exist_ok=True)

        dst_hdiffz = get_bin_path(hdiffz_name)
        dst_hpatchz = get_bin_path(hpatchz_name)

        shutil.copy2(hdiffz_src, dst_hdiffz)
        shutil.copy2(hpatchz_src, dst_hpatchz)

        # Set execution permissions on Unix
        if not is_win:
            os.chmod(dst_hdiffz, 0o755)
            os.chmod(dst_hpatchz, 0o755)

        log_ok(f"Binaries successfully installed to: {bin_dir}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def format_bytes_count(bytes_count: int) -> str:
    units = ['B', 'KB', 'MB', 'GB']
    val = float(bytes_count)
    i = 0
    while val >= 1024.0 and i < len(units) - 1:
        val /= 1024.0
        i += 1
    return f"{val:.2f} {units[i]}"
