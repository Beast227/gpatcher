import os
import sys
import shutil
from gpatcher.core.common import (
    log_info, log_warn, log_err, log_ok, remove_path_safe, to_native_path
)
from gpatcher.core.hash import get_file_sha256
from gpatcher.core.manifest import read_manifest_file

def invoke_restore(target: str, backup: str = 'latest', keep_backup: bool = False):
    """Restores the target directory to its pre-patch state using a stashed backup."""
    if not os.path.isdir(target):
        raise FileNotFoundError(f"Target directory not found: {target}")
        
    backup_dir = None
    if not backup or backup == 'latest':
        # Find latest backup folder in target
        candidates = []
        for d in os.listdir(target):
            full = os.path.join(target, d)
            if os.path.isdir(full) and d.startswith('.gpatcher-backup-'):
                candidates.append(full)
        if not candidates:
            raise FileNotFoundError(f"No backup dirs found in {target}")
        # Sort descending by folder name
        candidates.sort(reverse=True)
        backup_dir = candidates[0]
    elif os.path.isdir(backup):
        backup_dir = os.path.abspath(backup)
    else:
        maybe = os.path.join(target, backup)
        if os.path.isdir(maybe):
            backup_dir = os.path.abspath(maybe)
        else:
            raise FileNotFoundError(f"Backup folder not found: {backup}")
            
    log_info(f"Backup: {backup_dir}")
    manifest_path = os.path.join(backup_dir, '.gpatcher-manifest.json')
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Backup is missing .gpatcher-manifest.json -- cannot restore.")
        
    m = read_manifest_file(manifest_path)
    log_info(f"Restoring {m['game']}: {m['new_version']} -> {m['old_version']}")
    
    log_info("Pre-flight: verifying target looks patched...")
    mismatch = []
    for op in m['ops']:
        p = os.path.join(target, to_native_path(op['path']))
        exists = os.path.exists(p)
        op_type = op['op']
        
        if op_type in ('diff', 'add'):
            if not exists:
                mismatch.append(f"missing: {op['path']}")
            elif get_file_sha256(p) != op['new_sha256']:
                mismatch.append(f"not-at-new-version: {op['path']}")
        elif op_type == 'delete':
            if exists:
                mismatch.append(f"still-present: {op['path']}")
        elif op_type == 'keep':
            if not exists:
                mismatch.append(f"missing: {op['path']}")
            elif get_file_sha256(p) != op['sha256']:
                mismatch.append(f"modified: {op['path']}")
                
    if mismatch:
        log_err("Pre-flight failed -- target does not match the post-apply state recorded in backup:")
        for item in mismatch:
            log_err(f"  {item}")
        raise RuntimeError("Target has changed since the patch was applied. No restore performed.")
        
    log_ok("Pre-flight passed")
    
    for op in m['ops']:
        tgt = os.path.join(target, to_native_path(op['path']))
        op_type = op['op']
        
        if op_type == 'add':
            remove_path_safe(tgt)
            log_info(f"removed-add: {op['path']}")
        elif op_type in ('diff', 'delete'):
            src = os.path.join(backup_dir, to_native_path(op['path']))
            if not os.path.exists(src):
                raise FileNotFoundError(f"Backup is missing file needed for restore: {op['path']}")
            os.makedirs(os.path.dirname(tgt), exist_ok=True)
            shutil.copy2(src, tgt)
            if op_type == 'diff':
                log_info(f"restored:    {op['path']}")
            else:
                log_info(f"undeleted:   {op['path']}")
                
    log_info("Post-flight: verifying old-version hashes...")
    bad = 0
    for op in m['ops']:
        expected = None
        op_type = op['op']
        if op_type == 'diff':
            expected = op['old_sha256']
        elif op_type == 'delete':
            expected = op['old_sha256']
        elif op_type == 'keep':
            expected = op['sha256']
            
        if expected is None:
            continue
            
        p = os.path.join(target, to_native_path(op['path']))
        if not os.path.exists(p):
            log_err(f"  missing: {op['path']}")
            bad += 1
            continue
            
        if get_file_sha256(p) != expected:
            log_err(f"  hash mismatch: {op['path']}")
            bad += 1
            
    if bad > 0:
        raise RuntimeError(f"{bad} file(s) failed post-restore hash check. Backup kept at: {backup_dir}")
        
    log_ok(f"Restored to {m['old_version']}")
    
    if not keep_backup:
        remove_path_safe(backup_dir)
        log_info("Removed backup dir")
    else:
        log_info(f"Backup retained: {backup_dir}")
