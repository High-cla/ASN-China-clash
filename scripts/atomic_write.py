"""Atomic file replace helpers."""
from __future__ import annotations

import os
from pathlib import Path


def atomic_write(path: str | Path, content: str, encoding: str = "utf-8") -> None:
    """Write content via temp file + os.replace. Reject empty content."""
    if not content:
        raise ValueError(f"refusing empty write: {path}")
    target = Path(path)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    if tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise ValueError(f"refusing empty file: {path}")
    os.replace(tmp, target)
