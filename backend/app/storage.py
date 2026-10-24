"""Private upload storage and in-memory result registry.

* Uploads are written to a PRIVATE directory (never a web-served static folder)
  under server-generated UUID filenames.  The original filename is kept only as
  display metadata.
* Generated results are kept in memory (no database — out of scope for this
  MVP, per project constraints).  A result lives until the server restarts,
  which is sufficient for the demo journey: upload -> generate -> explore.

When persistence is later required, swap these dicts for a DB-backed store;
the API surface does not change.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from .schemas import SourceImage, StudyMaterial


@dataclass
class UploadRecord:
    upload_id: str
    stored_path: Path
    original_filename: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    stored_format: str

    def to_source_image(self) -> SourceImage:
        return SourceImage(
            upload_id=self.upload_id,
            filename=self.original_filename,
            content_type=self.content_type,
            size_bytes=self.size_bytes,
            width=self.width,
            height=self.height,
            url=f"/api/uploads/{self.upload_id}",
        )


class AppState:
    """Thread-safe in-memory stores."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.uploads: Dict[str, UploadRecord] = {}
        self.results: Dict[str, StudyMaterial] = {}

    def save_upload(self, record: UploadRecord) -> None:
        with self._lock:
            self.uploads[record.upload_id] = record

    def get_upload(self, upload_id: str) -> Optional[UploadRecord]:
        with self._lock:
            return self.uploads.get(upload_id)

    def save_result(self, result: StudyMaterial) -> None:
        with self._lock:
            self.results[result.result_id] = result

    def get_result(self, result_id: str) -> Optional[StudyMaterial]:
        with self._lock:
            return self.results.get(result_id)


state = AppState()


def ensure_upload_dir(upload_path: Path) -> Path:
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path
