import os
import re
import sys
import fnmatch
from typing import List, Dict
from gpatcher.core.common import assert_not_reparse, get_relative_path, log_info
from gpatcher.core.hash import get_file_sha256

DEFAULT_PATTERNS = [
    # Saves, userdata, settings
    r'(?:^|/|\\)(?:saves?|savegames?|userdata|profiles?)(?:$|/|\\)',
    r'\.(?:sav|save)$',
    # Steam emulators / cracks settings
    r'(?:^|/|\\)(?:steam_settings|steam_saves|steam_autocloud\.vdf)(?:$|/|\\)',
    r'steam_emu\.ini$',
    # Crash logs and debug symbols
    r'(?:^|/|\\)(?:logs?|crashes|crashdumps?)(?:$|/|\\)',
    r'\.(?:log|dmp|pdb|tmp|temp)$',
    # Cache / temporary
    r'(?:^|/|\\)(?:shadercache|cache)(?:$|/|\\)',
    r'\.cache$',
    # System junk
    r'desktop\.ini$',
    r'Thumbs\.db$',
    # Screenshots
    r'(?:^|/|\\)saved?screenshots?(?:$|/|\\)'
]

def test_is_excluded(rel_path: str, custom_excludes: List[str] = None) -> bool:
    """Matches a relative path against default game exclusions and custom glob patterns."""
    normalized = rel_path.replace('\\', '/')
    for pat in DEFAULT_PATTERNS:
        if re.search(pat, normalized, re.IGNORECASE):
            return True
    
    if custom_excludes:
        for glob in custom_excludes:
            if fnmatch.fnmatchcase(normalized, glob) or fnmatch.fnmatchcase(normalized.lower(), glob.lower()):
                return True
    return False

def get_file_tree(root: str, custom_excludes: List[str] = None) -> List[Dict]:
    """Walks the directory recursively, checking exclusions and hashing files."""
    root_abs = os.path.abspath(root)
    results = []
    excluded_count = 0
    
    all_files = []
    for dirpath, _, filenames in os.walk(root_abs):
        for f in filenames:
            full = os.path.join(dirpath, f)
            all_files.append(full)
            
    total = len(all_files)
    for idx, full in enumerate(all_files):
        assert_not_reparse(full)
        rel = get_relative_path(root_abs, full)
        
        if test_is_excluded(rel, custom_excludes):
            excluded_count += 1
            continue
            
        sha = get_file_sha256(full)
        size = os.path.getsize(full)
        results.append({
            'RelPath': rel,
            'Size': size,
            'Sha256': sha
        })
        
        if (idx + 1) % 25 == 0 or (idx + 1) == total:
            pct = ((idx + 1) / total) * 100 if total > 0 else 100
            sys.stdout.write(f"\rHashing {root}: {idx+1}/{total} ({pct:.1f}%)")
            sys.stdout.flush()
            
    if total > 0:
        print()
        
    if excluded_count > 0:
        log_info(f"Excluded {excluded_count} non-game file(s) (saves, logs, steam settings, etc.) from {root}")
        
    return results
