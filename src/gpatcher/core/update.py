import sys
import os
import urllib.request
import json
import re
import subprocess
from gpatcher.core.common import GPATCHER_VERSION, log_info, log_ok, log_warn, log_err, new_temp_dir, remove_path_safe
from gpatcher.tools.archive import expand_dir

def invoke_update(force: bool = False):
    """Checks for newer releases on GitHub and updates the gpatcher installation."""
    gpatcher_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    package_dir = os.path.dirname(gpatcher_dir)
    project_root = os.path.dirname(package_dir)

    # 1. Check if running from a Git repository
    curr = os.path.abspath(__file__)
    is_git_clone = False
    for _ in range(6):
        curr = os.path.dirname(curr)
        if os.path.exists(os.path.join(curr, '.git')):
            is_git_clone = True
            break
    if is_git_clone:
        log_warn("Running from a Git repository clone. Please use 'git pull' to update instead.")
        return

    log_info("Checking for updates...")
    repo = 'Beast227/gpatcher'
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(api_url, headers={'User-Agent': 'gpatcher-update'})
    try:
        with urllib.request.urlopen(req) as r:
            data = json.loads(r.read().decode('utf-8'))
    except Exception as e:
        raise RuntimeError(f"Failed to fetch latest release from GitHub: {e}")

    latest_tag = data.get('tag_name')
    if not latest_tag:
        raise RuntimeError("No release tag found on GitHub.")

    # Clean version strings for parsing/comparison
    clean_ver = lambda v: re.search(r'\d+(?:\.\d+)+', v).group(0) if re.search(r'\d+(?:\.\d+)+', v) else v
    latest_ver_str = clean_ver(latest_tag)
    current_ver_str = clean_ver(GPATCHER_VERSION)

    is_newer = False
    try:
        latest_parts = [int(x) for x in latest_ver_str.split('.')]
        current_parts = [int(x) for x in current_ver_str.split('.')]
        is_newer = latest_parts > current_parts
    except Exception:
        is_newer = latest_ver_str != current_ver_str

    if not is_newer and not force:
        log_ok(f"gpatcher is already up to date (v{GPATCHER_VERSION}).")
        return

    log_info(f"Updating gpatcher from v{GPATCHER_VERSION} to {latest_tag}...")

    # Check if installed as site-package or in-place
    is_site_package = 'site-packages' in package_dir or 'dist-packages' in package_dir

    if is_site_package:
        log_info("Upgrading via pip...")
        wheel_name = f"gpatcher-{latest_ver_str}-py3-none-any.whl"
        wheel_url = f"https://github.com/{repo}/releases/download/{latest_tag}/{wheel_name}"
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", wheel_url]
        log_info(f"Running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True)
            log_ok(f"Successfully updated gpatcher to {latest_tag}!")
            return
        except subprocess.CalledProcessError:
            log_warn("Wheel installation failed. Falling back to source installation from GitHub...")
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", f"git+https://github.com/{repo}.git"]
            try:
                subprocess.run(cmd, check=True)
                log_ok(f"Successfully updated gpatcher to {latest_tag}!")
                return
            except subprocess.CalledProcessError as e:
                raise RuntimeError(f"Pip upgrade failed: {e}")

    else:
        # In-place zip upgrade
        log_info("Performing in-place upgrade...")
        assets = data.get('assets', [])
        zip_asset = None
        for asset in assets:
            name = asset.get('name', '')
            if name.endswith('.zip') and not 'hdiffpatch' in name.lower():
                zip_asset = asset
                break
        if not zip_asset:
            zip_url = data.get('zipball_url')
        else:
            zip_url = zip_asset.get('browser_download_url')

        if not zip_url:
            raise RuntimeError(f"No zip asset or source zip found in release {latest_tag}")

        staging = new_temp_dir('gpatcher-update')
        zip_path = os.path.join(staging, 'gpatcher-update.zip')
        try:
            log_info(f"Downloading update from {zip_url}...")
            urllib.request.urlretrieve(zip_url, zip_path)

            extract_dir = os.path.join(staging, 'extract')
            log_info("Extracting update...")
            expand_dir(zip_path, extract_dir)

            src_folder = extract_dir
            subdirs = os.listdir(extract_dir)
            if len(subdirs) == 1 and os.path.isdir(os.path.join(extract_dir, subdirs[0])):
                src_folder = os.path.join(extract_dir, subdirs[0])

            log_info("Applying update files...")
            import shutil
            for item in os.listdir(src_folder):
                src_item = os.path.join(src_folder, item)
                dst_item = os.path.join(project_root, item)
                if item in ('.git', '.gitignore', 'bin'):
                    continue
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dst_item, dirs_exist_ok=True)
                else:
                    shutil.copy2(src_item, dst_item)

            if sys.platform != 'win32':
                for wrapper in ('gpatcher',):
                    wpath = os.path.join(project_root, wrapper)
                    if os.path.exists(wpath):
                        os.chmod(wpath, 0o755)

            log_ok(f"Successfully updated gpatcher to {latest_tag}!")
        finally:
            remove_path_safe(staging)
