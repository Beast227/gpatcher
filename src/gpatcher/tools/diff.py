import subprocess
import sys
import os
from gpatcher.core.common import get_bin_path

def _get_bin(name: str) -> str:
    bin_ext = '.exe' if sys.platform == 'win32' else ''
    exe = get_bin_path(f"{name}{bin_ext}")
    if not os.path.exists(exe):
        from gpatcher.tools.fetch import fetch_hdiffpatch
        try:
            fetch_hdiffpatch()
        except Exception as e:
            raise FileNotFoundError(
                f"Binary '{name}{bin_ext}' not found at {exe} and auto-download failed: {e}.\n"
                f"Please run diagnostics or fetch: gpatcher doctor"
            )
    if not os.path.exists(exe):
        raise FileNotFoundError(
            f"Binary '{name}{bin_ext}' not found at {exe} even after successful auto-download.\n"
            f"Please run diagnostics or fetch: gpatcher doctor"
        )
    return exe

def invoke_hdiffz(old_file: str, new_file: str, patch_out: str):
    """Executes hdiffz to generate a binary delta patch between two files."""
    exe = _get_bin('hdiffz')
    cmd = [exe, '-f', old_file, new_file, patch_out]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"hdiffz failed (exit {e.returncode}) on {old_file} -> {new_file}\n"
            f"Stderr: {e.stderr}"
        )

def invoke_hpatchz(old_file: str, patch_file: str, new_out: str):
    """Executes hpatchz to apply a binary delta patch to an old file, producing the new file."""
    exe = _get_bin('hpatchz')
    cmd = [exe, '-f', old_file, patch_file, new_out]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"hpatchz failed (exit {e.returncode}) on {old_file} + {patch_file}\n"
            f"Stderr: {e.stderr}"
        )
