import json
import re
from datetime import datetime, timezone
from gpatcher.core.common import GPATCHER_VERSION

def get_game_slug(name: str) -> str:
    """Generates a clean URL-friendly slug from the game name."""
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    if len(s) > 60:
        s = s[:60].rstrip('-')
    if not s:
        raise ValueError(f"Game name produces empty slug: {name}")
    return s

def new_manifest(game: str, old_version: str, new_version: str, old_root_hash: str, new_root_hash: str, ops: list) -> dict:
    """Constructs a standard gpatcher manifest dictionary."""
    return {
        'schema': 1,
        'tool': f"gpatcher {GPATCHER_VERSION}",
        'game': game,
        'game_slug': get_game_slug(game),
        'old_version': old_version,
        'new_version': new_version,
        'created_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'old_root_sha256': old_root_hash,
        'new_root_sha256': new_root_hash,
        'ops': ops
    }

def write_manifest_file(manifest: dict, path: str):
    """Writes a manifest dictionary to file as formatted JSON."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

def read_manifest_file(path: str) -> dict:
    """Reads a manifest file, validating that the schema is supported."""
    with open(path, 'r', encoding='utf-8') as f:
        m = json.load(f)
    if m.get('schema') != 1:
        raise ValueError(f"Unsupported manifest schema: {m.get('schema')} (expected 1)")
    return m
