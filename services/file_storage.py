"""File storage service providing isolated per-run directories and path traversal protection."""

import os
import uuid
import re
from pathlib import Path
from typing import Optional, Tuple, Union

BASE_OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "outputs")).resolve()
BASE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Safe filename pattern: alphanumeric, hyphen, underscore, and dot
SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


class FileStorageService:
    """Manages isolated storage per workflow run and safe downloads."""

    @staticmethod
    def create_run_dir(prefix: str = "run") -> Tuple[str, Path]:
        """Creates a unique directory for a run under outputs/<run_id>/."""
        clean_prefix = re.sub(r"[^a-zA-Z0-9_\-]", "", prefix) or "run"
        run_id = f"{clean_prefix}_{uuid.uuid4().hex[:12]}"
        run_dir = BASE_OUTPUT_DIR / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_id, run_dir

    @staticmethod
    def get_run_dir(run_id: str) -> Optional[Path]:
        """Resolves run directory while preventing traversal."""
        if not run_id or not SAFE_FILENAME_RE.match(run_id):
            return None
        run_dir = (BASE_OUTPUT_DIR / run_id).resolve()
        try:
            run_dir.relative_to(BASE_OUTPUT_DIR)
        except ValueError:
            return None
        if not run_dir.exists() or not run_dir.is_dir():
            return None
        return run_dir

    @staticmethod
    def save_file(
        run_id: str,
        filename: str,
        content: Union[str, bytes],
        encoding: str = "utf-8",
    ) -> Path:
        """Saves content into a specific run's directory."""
        if not SAFE_FILENAME_RE.match(filename):
            raise ValueError(f"Invalid filename: {filename}")
        run_dir = FileStorageService.get_run_dir(run_id)
        if not run_dir:
            run_dir = BASE_OUTPUT_DIR / run_id
            run_dir.mkdir(parents=True, exist_ok=True)

        target_file = run_dir / filename
        if isinstance(content, str):
            target_file.write_text(content, encoding=encoding)
        else:
            target_file.write_bytes(content)
        return target_file

    @staticmethod
    def get_file_path(run_id: str, filename: str) -> Optional[Path]:
        """Securely retrieves the Path to a file in a run directory."""
        if not SAFE_FILENAME_RE.match(run_id) or not SAFE_FILENAME_RE.match(filename):
            return None

        run_dir = FileStorageService.get_run_dir(run_id)
        if not run_dir:
            return None

        file_path = (run_dir / filename).resolve()
        try:
            file_path.relative_to(run_dir)
        except ValueError:
            # Traversal attempt
            return None

        if not file_path.exists() or not file_path.is_file():
            return None

        return file_path
