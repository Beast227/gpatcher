import sys
from gpatcher.core.common import log_info, log_ok, log_warn, log_err

def invoke_doctor() -> bool:
    """Performs system diagnostic checks on the dependencies and environment."""
    log_info("gpatcher doctor")
    all_ok = True
    try:
        import detools
        version = getattr(detools, '__version__', 'installed')
        log_ok(f"detools: {version}")
    except ImportError:
        log_err("detools: MISSING -- run: pip install detools")
        all_ok = False
            
    log_ok(f"python: {sys.version.split()[0]}")
    
    try:
        import internetarchive
        # Some versions might not expose __version__ directly on top level, handle with fallback
        version = getattr(internetarchive, '__version__', 'installed')
        log_ok(f"internetarchive: {version}")
    except ImportError:
        log_warn("internetarchive: not found -- run: pip install internetarchive")
        
    return all_ok
