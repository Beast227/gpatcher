import os
import shutil
from typing import List
from gpatcher.core.common import (
    log_info, log_ok, new_temp_dir, remove_path_safe,
    to_native_path, format_bytes
)
from gpatcher.core.walk import get_file_tree
from gpatcher.core.hash import get_merkle_root
from gpatcher.core.manifest import new_manifest, write_manifest_file, get_game_slug
from gpatcher.tools.diff import invoke_hdiffz
from gpatcher.tools.archive import compress_dir

def invoke_create(old_dir: str, new_dir: str, game: str, old_ver: str, new_ver: str, out_dir: str = '.', exclude: List[str] = None) -> str:
    """Generates a delta patch package (*.patch.zip) between two game installations."""
    if not os.path.isdir(old_dir):
        raise FileNotFoundError(f"Old directory not found: {old_dir}")
    if not os.path.isdir(new_dir):
        raise FileNotFoundError(f"New directory not found: {new_dir}")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        
    log_info(f"Hashing old install: {old_dir}")
    old_files = get_file_tree(old_dir, exclude)
    log_info(f"Hashing new install: {new_dir}")
    new_files = get_file_tree(new_dir, exclude)
    
    old_map = {f['RelPath']: f for f in old_files}
    new_map = {f['RelPath']: f for f in new_files}
    
    staging = new_temp_dir('gpatcher-create')
    log_info(f"Staging: {staging}")
    
    diff_dir = os.path.join(staging, 'diff')
    add_dir = os.path.join(staging, 'add')
    os.makedirs(diff_dir, exist_ok=True)
    os.makedirs(add_dir, exist_ok=True)
    
    ops = []
    total_diff = 0
    total_add = 0
    count_diff = 0
    count_add = 0
    count_del = 0
    count_keep = 0
    
    for rel, nf in new_map.items():
        if rel in old_map:
            of = old_map[rel]
            if of['Sha256'] == nf['Sha256']:
                ops.append({
                    'op': 'keep',
                    'path': rel,
                    'sha256': nf['Sha256']
                })
                count_keep += 1
            else:
                patch_rel = f"{rel}.hdiff"
                patch_path = os.path.join(diff_dir, to_native_path(patch_rel))
                os.makedirs(os.path.dirname(patch_path), exist_ok=True)
                
                old_full = os.path.join(old_dir, to_native_path(rel))
                new_full = os.path.join(new_dir, to_native_path(rel))
                
                log_info(f"diff: {rel}")
                invoke_hdiffz(old_full, new_full, patch_path)
                psize = os.path.getsize(patch_path)
                total_diff += psize
                ops.append({
                    'op': 'diff',
                    'path': rel,
                    'old_sha256': of['Sha256'],
                    'new_sha256': nf['Sha256'],
                    'patch': f"diff/{patch_rel}",
                    'patch_size': psize
                })
                count_diff += 1
        else:
            dst_path = os.path.join(add_dir, to_native_path(rel))
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            src_full = os.path.join(new_dir, to_native_path(rel))
            shutil.copy2(src_full, dst_path)
            
            log_info(f"add:  {rel}")
            total_add += nf['Size']
            ops.append({
                'op': 'add',
                'path': rel,
                'new_sha256': nf['Sha256'],
                'src': f"add/{rel}",
                'size': nf['Size']
            })
            count_add += 1
            
    for rel, of in old_map.items():
        if rel not in new_map:
            log_info(f"del:  {rel}")
            ops.append({
                'op': 'delete',
                'path': rel,
                'old_sha256': of['Sha256']
            })
            count_del += 1
            
    old_h = {k: v['Sha256'] for k, v in old_map.items()}
    new_h = {k: v['Sha256'] for k, v in new_map.items()}
    old_root = get_merkle_root(old_h)
    new_root = get_merkle_root(new_h)
    
    manifest = new_manifest(
        game=game,
        old_version=old_ver,
        new_version=new_ver,
        old_root_hash=old_root,
        new_root_hash=new_root,
        ops=ops
    )
    
    write_manifest_file(manifest, os.path.join(staging, 'manifest.json'))
    
    slug = get_game_slug(game)
    bundle = os.path.join(out_dir, f"{slug}_{old_ver}_to_{new_ver}.patch.zip")
    log_info(f"Packing: {bundle}")
    compress_dir(staging, bundle)
    
    bundle_size = os.path.getsize(bundle)
    log_ok(f"Bundle: {bundle}")
    log_ok(f"  size:    {format_bytes(bundle_size)}")
    log_ok(f"  diff:    {count_diff} files ({format_bytes(total_diff)})")
    log_ok(f"  add:     {count_add} files ({format_bytes(total_add)})")
    log_ok(f"  delete:  {count_del} files")
    log_ok(f"  keep:    {count_keep} files")
    
    remove_path_safe(staging)
    return bundle
