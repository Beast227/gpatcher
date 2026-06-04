import os
import sys
from gpatcher.core.common import (
    log_info, log_err, log_ok, new_temp_dir, remove_path_safe, to_native_path
)
from gpatcher.core.hash import get_file_sha256
from gpatcher.core.manifest import read_manifest_file
from gpatcher.tools.archive import expand_dir

def invoke_verify(install_dir: str, against_path: str):
    """Verifies that an install directory matches the expected manifest/bundle snapshot."""
    if not os.path.isdir(install_dir):
        raise FileNotFoundError(f"Install directory not found: {install_dir}")
    if not os.path.exists(against_path):
        raise FileNotFoundError(f"Manifest/bundle not found: {against_path}")
        
    staging = None
    try:
        manifest_path = None
        if against_path.lower().endswith('.zip'):
            staging = new_temp_dir('gpatcher-verify')
            expand_dir(against_path, staging)
            manifest_path = os.path.join(staging, 'manifest.json')
        else:
            manifest_path = against_path
            
        m = read_manifest_file(manifest_path)
        log_info(f"Verifying {install_dir} against {m['game']} {m['old_version']} snapshot")
        
        bad = 0
        total_ops = len(m['ops'])
        for idx, op in enumerate(m['ops']):
            if (idx + 1) % 25 == 0 or (idx + 1) == total_ops:
                pct = ((idx + 1) / total_ops) * 100 if total_ops > 0 else 100
                sys.stdout.write(f"\rVerifying files: {idx+1}/{total_ops} ({pct:.1f}%)")
                sys.stdout.flush()
                
            expected = None
            op_type = op['op']
            if op_type == 'keep':
                expected = op['sha256']
            elif op_type in ('diff', 'delete'):
                expected = op['old_sha256']
            elif op_type == 'add':
                continue
                
            if expected is None:
                continue
                
            p = os.path.join(install_dir, to_native_path(op['path']))
            if not os.path.exists(p):
                log_err(f"  missing: {op['path']}")
                bad += 1
                continue
                
            if get_file_sha256(p) != expected:
                log_err(f"  modified: {op['path']}")
                bad += 1
                
        if total_ops > 0:
            print()
            
        if bad == 0:
            log_ok("Install matches expected old snapshot")
        else:
            raise ValueError(f"{bad} file(s) differ from expected")
    finally:
        if staging:
            remove_path_safe(staging)
