"""APFS clonefile research primitives; not yet integrated into native forks."""
from __future__ import annotations
import ctypes
import os
import shutil
from pathlib import Path

def clone_file(source: Path, target: Path) -> bool:
    """Attempt an APFS clone. Returns False when clonefile is unavailable."""
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        clonefile = libc.clonefile
        clonefile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32]
        clonefile.restype = ctypes.c_int
        result = clonefile(os.fsencode(source), os.fsencode(target), 0)
        if result == 0:
            return True
    except (AttributeError, OSError):
        pass
    shutil.copy2(source, target)
    return False

def logical_bytes(path: Path) -> int:
    return path.stat().st_size

def allocated_bytes(path: Path) -> int:
    return path.stat().st_blocks * 512
