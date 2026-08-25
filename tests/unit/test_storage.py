from pathlib import Path

from decastate.storage.local import atomic_copy
from decastate.utils.hashing import sha256_file


def test_atomic_copy_has_integrity_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    target = tmp_path / "nested" / "target.bin"
    source.write_bytes(b"decastate-production-storage")
    info = atomic_copy(source, target)
    assert info["bytes"] == source.stat().st_size
    assert info["sha256"] == sha256_file(target)
    assert target.read_bytes() == source.read_bytes()
