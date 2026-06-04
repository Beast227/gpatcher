import os
import re
import sys
import json

def get_win_exe_version(filepath: str) -> str:
    """Reads the product/file version from a Windows executable using standard library ctypes."""
    import ctypes
    from ctypes import wintypes
    
    class VS_FIXEDFILEINFO(ctypes.Structure):
        _fields_ = [
            ("dwSignature", wintypes.DWORD),
            ("dwStrucVersion", wintypes.DWORD),
            ("dwFileVersionMS", wintypes.DWORD),
            ("dwFileVersionLS", wintypes.DWORD),
            ("dwProductVersionMS", wintypes.DWORD),
            ("dwProductVersionLS", wintypes.DWORD),
            ("dwFileFlagsMask", wintypes.DWORD),
            ("dwFileFlags", wintypes.DWORD),
            ("dwFileOS", wintypes.DWORD),
            ("dwFileType", wintypes.DWORD),
            ("dwFileSubtype", wintypes.DWORD),
            ("dwFileDateMS", wintypes.DWORD),
            ("dwFileDateLS", wintypes.DWORD),
        ]
        
    try:
        dwLen = ctypes.windll.version.GetFileVersionInfoSizeW(filepath, None)
        if not dwLen:
            return None
        lpData = ctypes.create_string_buffer(dwLen)
        if not ctypes.windll.version.GetFileVersionInfoW(filepath, 0, dwLen, lpData):
            return None
            
        # 1. Query ProductVersion string
        puLen = ctypes.c_uint()
        lpTranslate = ctypes.c_void_p()
        subblock = "\\StringFileInfo\\040904b0\\ProductVersion"
        if ctypes.windll.version.VerQueryValueW(lpData, "\\VarFileInfo\\Translation", ctypes.byref(lpTranslate), ctypes.byref(puLen)):
            if puLen.value >= 4:
                pTrans = ctypes.cast(lpTranslate, ctypes.POINTER(ctypes.c_ushort))
                lang = pTrans[0]
                codepage = pTrans[1]
                subblock = f"\\StringFileInfo\\{lang:04x}{codepage:04x}\\ProductVersion"
                
        lpBuffer = ctypes.c_void_p()
        if ctypes.windll.version.VerQueryValueW(lpData, subblock, ctypes.byref(lpBuffer), ctypes.byref(puLen)):
            val = ctypes.wstring_at(lpBuffer)
            if val and val.strip() and val.strip() != "0.0.0.0":
                return val.strip()
                
        # 2. Query FileVersion string as fallback
        subblock_file = subblock.replace("ProductVersion", "FileVersion")
        if ctypes.windll.version.VerQueryValueW(lpData, subblock_file, ctypes.byref(lpBuffer), ctypes.byref(puLen)):
            val = ctypes.wstring_at(lpBuffer)
            if val and val.strip() and val.strip() != "0.0.0.0":
                return val.strip()
                
        # 3. Query Fixed info (binary structure)
        if ctypes.windll.version.VerQueryValueW(lpData, "\\", ctypes.byref(lpBuffer), ctypes.byref(puLen)):
            ffi = VS_FIXEDFILEINFO.from_address(lpBuffer.value)
            prod_ver = (
                (ffi.dwProductVersionMS >> 16) & 0xffff,
                ffi.dwProductVersionMS & 0xffff,
                (ffi.dwProductVersionLS >> 16) & 0xffff,
                ffi.dwProductVersionLS & 0xffff
            )
            version_str = f"{prod_ver[0]}.{prod_ver[1]}.{prod_ver[2]}.{prod_ver[3]}"
            if version_str != "0.0.0.0":
                return version_str
    except Exception:
        pass
    return None

def parse_version_file(filepath: str) -> str:
    """Parses a version file (JSON, INI, CFG, or plain text) and extracts the version string."""
    name = os.path.basename(filepath).lower()
    version_regex = re.compile(r'\b\d+\.\d+(?:\.\d+)*(?:-[a-zA-Z0-9.]+)?\b')
    
    try:
        if name.endswith('.json'):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)
                
            def find_ver_key(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k.lower() in ('version', 'app_version', 'game_version'):
                            if isinstance(v, (str, int, float)):
                                return str(v).strip()
                        res = find_ver_key(v)
                        if res:
                            return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = find_ver_key(item)
                        if res:
                            return res
                return None
                
            res = find_ver_key(data)
            if res:
                return res
                
        elif name.endswith('.ini') or name.endswith('.cfg'):
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if '=' in line or ':' in line:
                        parts = re.split(r'[=:]', line, 1)
                        key = parts[0].strip().lower()
                        val = parts[1].strip()
                        if 'version' in key or 'ver' in key:
                            m = version_regex.search(val)
                            if m:
                                return m.group(0)
                                
        else: # Text files or Unity files
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                # Check first 20 lines to avoid reading massive files
                for _ in range(20):
                    line = f.readline()
                    if not line:
                        break
                    # Look for lines with 'version' or 'ver' followed by version
                    if any(x in line.lower() for x in ('version', 'ver', 'v')):
                        m = version_regex.search(line)
                        if m:
                            return m.group(0)
                # Fallback to search first line matching the pattern
                f.seek(0)
                for _ in range(20):
                    line = f.readline()
                    if not line:
                        break
                    m = version_regex.search(line)
                    if m:
                        return m.group(0)
    except Exception:
        pass
    return None

def detect_version(directory: str) -> str:
    """Attempts to auto-detect the game version from a directory."""
    if not os.path.isdir(directory):
        return None

    # 1. macOS plist detection
    if sys.platform == 'darwin':
        for root, dirs, files in os.walk(directory):
            for d in dirs:
                if d.endswith('.app'):
                    plist_path = os.path.join(root, d, 'Contents', 'Info.plist')
                    if os.path.exists(plist_path):
                        try:
                            import plistlib
                            with open(plist_path, 'rb') as fp:
                                plist = plistlib.load(fp)
                                ver = plist.get('CFBundleShortVersionString') or plist.get('CFBundleVersion')
                                if ver:
                                    return str(ver).strip()
                        except Exception:
                            pass

    # 2. Windows Executable Version info
    if sys.platform == 'win32':
        exe_files = []
        try:
            for f in os.listdir(directory):
                if f.lower().endswith('.exe'):
                    exe_files.append(os.path.join(directory, f))
        except Exception:
            pass
        
        valid_exes = []
        exclude_patterns = ['crash', 'unity', 'setup', 'install', 'uninst', 'tool', 'config', 'helper', 'register', 'vcredist', 'dxsetup', 'cef', 'update']
        for exe in exe_files:
            name = os.path.basename(exe).lower()
            if any(p in name for p in exclude_patterns):
                continue
            valid_exes.append(exe)
        
        valid_exes.sort(key=lambda p: os.path.getsize(p), reverse=True)
        
        for exe in valid_exes:
            ver = get_win_exe_version(exe)
            if ver:
                return ver

    # 3. Common version files in root/subdirectories
    common_names = ['version.txt', 'version.json', 'package.json', 'app.info', 'game.ini', 'project.json']
    for depth in (0, 1):
        for root, dirs, files in os.walk(directory):
            rel_path = os.path.relpath(root, directory)
            curr_depth = 0 if rel_path == '.' else len(rel_path.split(os.path.sep))
            if curr_depth != depth:
                continue

            for f in files:
                if f.lower() in common_names:
                    filepath = os.path.join(root, f)
                    ver = parse_version_file(filepath)
                    if ver:
                        return ver
            if depth == 1:
                break

    # 4. Fallback search for any version text file
    for root, dirs, files in os.walk(directory):
        rel_path = os.path.relpath(root, directory)
        curr_depth = 0 if rel_path == '.' else len(rel_path.split(os.path.sep))
        if curr_depth > 1:
            continue
        for f in files:
            if 'version' in f.lower() and f.lower().endswith(('.txt', '.cfg', '.ini')):
                filepath = os.path.join(root, f)
                ver = parse_version_file(filepath)
                if ver:
                    return ver

    return None
