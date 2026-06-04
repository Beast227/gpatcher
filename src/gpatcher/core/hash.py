import hashlib

def get_file_sha256(path: str) -> str:
    """Computes the SHA-256 hash of a file, returning a lowercase hex string."""
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            sha.update(chunk)
    return sha.hexdigest().lower()

def get_merkle_root(path_hash_map: dict) -> str:
    """Computes a deterministic root hash over sorted dictionary keys/hashes."""
    sha = hashlib.sha256()
    for k in sorted(path_hash_map.keys()):
        line = f"{k}:{path_hash_map[k]}\n"
        sha.update(line.encode('utf-8'))
    return sha.hexdigest().lower()
