"""Streaming file hashes shared by model artifacts and package snapshots."""

import hashlib
from pathlib import Path


def file_md5(path: Path | str) -> str:
    digest = hashlib.md5()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
