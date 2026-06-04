import sys
import os
from gpatcher.core.common import get_bin_path, log_info, log_ok, log_warn, log_err, format_bytes

def invoke_doctor() -> bool:
    """Performs system diagnostic checks on the dependencies and environment."""
    log_info("gpatcher doctor")
    is_win = sys.platform == 'win32'
    bin_ext = '.exe' if is_win else ''
    
    hdiffz = get_bin_path(f"hdiffz{bin_ext}")
    hpatchz = get_bin_path(f"hpatchz{bin_ext}")
    
    all_ok = True
    for e in (hdiffz, hpatchz):
        leaf = os.path.basename(e)
        if os.path.exists(e):
            sz = os.path.getsize(e)
            log_ok(f"  {leaf}: {format_bytes(sz)}")
        else:
            log_err(f"  {leaf}: MISSING -- run: gpatcher fetch")
            all_ok = False
            
    log_ok(f"  python: {sys.version.split()[0]}")
    
    try:
        import internetarchive
        # Some versions might not expose __version__ directly on top level, handle with fallback
        version = getattr(internetarchive, '__version__', 'installed')
        log_ok(f"  internetarchive: {version}")
    except ImportError:
        log_warn("  internetarchive: not found -- run: pip install internetarchive")
        
    return all_ok
