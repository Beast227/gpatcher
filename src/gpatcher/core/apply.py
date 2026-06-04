import os
import sys
import shutil
import urllib.request
from datetime import datetime
from gpatcher.core.common import (
    log_info, log_warn, log_err, log_ok, new_temp_dir, remove_path_safe,
    to_native_path
)
from gpatcher.core.hash import get_file_sha256
from gpatcher.core.manifest import read_manifest_file, write_manifest_file, get_game_slug
from gpatcher.tools.archive import expand_dir
from gpatcher.tools.diff import invoke_hpatchz

def invoke_apply(patch_path: str, target: str, dry_run: bool = False, no_backup: bool = False, keep_backup: bool = False):
    """Applies a patch package to a target directory, performing integrity and rollback checks."""
    if not os.path.isdir(target):
        raise FileNotFoundError(f"Target directory not found: {target}")
        
    staging = new_temp_dir('gpatcher-apply')
    try:
        patch_local = patch_path
        unpacked = None
        skip_unpack = False
        
        # Download patch if it's a URL
        if patch_path.startswith(('http://', 'https://')):
            patch_local = os.path.join(staging, 'patch.zip')
            log_info(f"Downloading: {patch_path}")
            urllib.request.urlretrieve(patch_path, patch_local)
        elif os.path.isdir(patch_path):
            if os.path.exists(os.path.join(patch_path, 'manifest.json')):
                unpacked = patch_path
                skip_unpack = True
            else:
                zips = [os.path.join(patch_path, f) for f in os.listdir(patch_path) if f.endswith('.zip')]
                if zips:
                    patch_local = zips[0]
                    log_info(f"Found patch ZIP: {os.path.basename(patch_local)}")
                else:
                    raise FileNotFoundError(f"Patch directory does not contain 'manifest.json' or any ZIP files: {patch_path}")
                    
        if not skip_unpack:
            log_info("Unpacking patch...")
            unpacked = os.path.join(staging, 'unpack')
            expand_dir(patch_local, unpacked)
            
        manifest_path = os.path.join(unpacked, 'manifest.json')
        m = read_manifest_file(manifest_path)
        log_info(f"{m['game']} {m['old_version']} -> {m['new_version']} ({len(m['ops'])} ops)")
        
        log_info("Pre-flight: verifying old install...")
        mismatch = []
        total_verify = len(m['ops'])
        for idx, op in enumerate(m['ops']):
            if (idx + 1) % 25 == 0 or (idx + 1) == total_verify:
                pct = ((idx + 1) / total_verify) * 100 if total_verify > 0 else 100
                sys.stdout.write(f"\rPre-flight: checking files: {idx+1}/{total_verify} ({pct:.1f}%)")
                sys.stdout.flush()
                
            p = os.path.join(target, to_native_path(op['path']))
            exists = os.path.exists(p)
            if op['op'] == 'add':
                continue
            if not exists:
                mismatch.append(f"missing: {op['path']}")
                continue
                
            expected = None
            if op['op'] == 'keep':
                expected = op['sha256']
            elif op['op'] in ('diff', 'delete'):
                expected = op['old_sha256']
                
            if expected:
                if get_file_sha256(p) != expected:
                    mismatch.append(f"modified: {op['path']}")
                    
        if total_verify > 0:
            print()
            
        if mismatch:
            log_err("Pre-flight failed:")
            for item in mismatch:
                log_err(f"  {item}")
            raise RuntimeError("Wrong old version or tampered install. No changes made.")
            
        log_ok("Pre-flight passed")
        
        if dry_run:
            log_info("Dry run -- no changes applied")
            return
            
        backup_dir = None
        if not no_backup:
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            backup_dir = os.path.join(target, f".gpatcher-backup-{timestamp}")
            os.makedirs(backup_dir, exist_ok=True)
            log_info(f"Backup: {backup_dir}")
            
            backup_ops = [op for op in m['ops'] if op['op'] in ('diff', 'delete')]
            total_backup = len(backup_ops)
            for idx, op in enumerate(backup_ops):
                pct = ((idx + 1) / total_backup) * 100 if total_backup > 0 else 100
                sys.stdout.write(f"\rCreating backup: {idx+1}/{total_backup} ({pct:.1f}%)")
                sys.stdout.flush()
                
                src = os.path.join(target, to_native_path(op['path']))
                dst = os.path.join(backup_dir, to_native_path(op['path']))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            if total_backup > 0:
                print()
            
            # Save manifest in backup for restore
            write_manifest_file(m, os.path.join(backup_dir, '.gpatcher-manifest.json'))
            
        try:
            total_ops = len(m['ops'])
            for idx, op in enumerate(m['ops']):
                pct = ((idx + 1) / total_ops) * 100 if total_ops > 0 else 100
                sys.stdout.write(f"\rApplying patch: {idx+1}/{total_ops} ({pct:.1f}%)")
                sys.stdout.flush()
                
                tgt = os.path.join(target, to_native_path(op['path']))
                op_type = op['op']
                
                if op_type == 'diff':
                    patch_file = os.path.join(unpacked, to_native_path(op['patch']))
                    tmp_out = f"{tgt}.gpatcher-new"
                    invoke_hpatchz(tgt, patch_file, tmp_out)
                    
                    if get_file_sha256(tmp_out) != op['new_sha256']:
                        remove_path_safe(tmp_out)
                        raise ValueError(f"Post-patch hash mismatch: {op['path']}")
                    # Atomic replace
                    remove_path_safe(tgt)
                    shutil.move(tmp_out, tgt)
                    
                elif op_type == 'add':
                    src_file = os.path.join(unpacked, to_native_path(op['src']))
                    os.makedirs(os.path.dirname(tgt), exist_ok=True)
                    shutil.copy2(src_file, tgt)
                    
                    if get_file_sha256(tgt) != op['new_sha256']:
                        raise ValueError(f"Post-add hash mismatch: {op['path']}")
                        
                elif op_type == 'delete':
                    remove_path_safe(tgt)
            if total_ops > 0:
                print()
                
            log_ok("Patch applied successfully")
            
            if backup_dir:
                if keep_backup:
                    log_info(f"Backup retained at: {backup_dir}")
                else:
                    remove_path_safe(backup_dir)
                    log_info("Temporary backup cleaned up (use --keep-backup to retain it for restore)")
                    
        except Exception as apply_err:
            log_err(f"Apply failed: {apply_err}")
            if backup_dir and os.path.isdir(backup_dir):
                log_warn("Rolling back from backup...")
                # Restore files from backup recursively
                for root, _, files in os.walk(backup_dir):
                    for file in files:
                        if file == '.gpatcher-manifest.json':
                            continue
                        src_full = os.path.join(root, file)
                        rel = os.path.relpath(src_full, backup_dir)
                        rt = os.path.join(target, rel)
                        os.makedirs(os.path.dirname(rt), exist_ok=True)
                        shutil.copy2(src_full, rt)
                log_warn("Rollback complete")
            raise apply_err
    finally:
        remove_path_safe(staging)
