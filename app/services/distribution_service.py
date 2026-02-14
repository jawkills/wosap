from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class DistributionService:
    def __init__(self, default_destination_base: str = "//sdcard/XPersonal") -> None:
        self.default_destination_base = default_destination_base

    def sanitize_destination_base(self, raw_base: str) -> Tuple[str, str]:
        base = (raw_base or "").strip()
        if len(base) > 1 and base[0] == base[-1] and base[0] in {'"', "'"}:
            base = base[1:-1].strip()

        if not base:
            fallback = self.default_destination_base
            return fallback, f"Base folder tidak valid. Menggunakan default: {fallback}"

        base = base.replace("\\", "/")
        if re.search(r"[`$;&|<>\n\r\"']", base):
            fallback = self.default_destination_base
            return fallback, f"Base folder tidak valid. Menggunakan default: {fallback}"

        if not base.startswith("/"):
            base = f"//sdcard/{base.lstrip('/')}"

        if base.startswith("//"):
            normalized_rest = re.sub(r"/{2,}", "/", base[2:])
            base = f"//{normalized_rest}"
        else:
            normalized_rest = re.sub(r"/{2,}", "/", base.lstrip("/"))
            base = f"/{normalized_rest}"

        base = base.rstrip("/")
        if not base or base in {"/", "//"}:
            fallback = self.default_destination_base
            return fallback, f"Base folder tidak valid. Menggunakan default: {fallback}"

        return base, ""

    def build_remote_path(
        self, destination_base: str, destination_mode: str
    ) -> Tuple[str, str]:
        sanitized_base, warning = self.sanitize_destination_base(destination_base)
        if destination_mode == "manual":
            return sanitized_base, warning
        today_folder = datetime.now().strftime("%Y%m%d")
        return f"{sanitized_base}/{today_folder}", warning

    def get_sorted_files(self, src_dir: str) -> List[str]:
        src_path = Path(src_dir)
        files: List[str] = []
        for file_path in src_path.rglob("*"):
            if not file_path.is_file():
                continue
            if not file_path.name.lower().endswith(".tar.gz"):
                continue
            rel_path = file_path.relative_to(src_path).as_posix()
            files.append(rel_path)

        def extract_sort_key(rel_path: str) -> int:
            match = re.search(r"-(\d{3})-", Path(rel_path).name)
            if not match:
                return 0
            return int(match.group(1))

        files.sort(key=lambda item: (extract_sort_key(item), item.lower()))
        return files

    def validate_files(
        self, src_dir: str, files: List[str]
    ) -> Tuple[List[str], List[str]]:
        valid_files: List[str] = []
        errors: List[str] = []

        for rel_path in files:
            abs_path = Path(src_dir) / rel_path
            try:
                if abs_path.stat().st_size == 0:
                    errors.append(f"{rel_path}: File kosong")
                    continue
                with abs_path.open("rb") as handle:
                    if handle.read(2) != b"\x1f\x8b":
                        errors.append(f"{rel_path}: Format tidak valid")
                        continue
                valid_files.append(rel_path)
            except Exception as exc:
                errors.append(f"{rel_path}: {exc}")

        return valid_files, errors

    def calculate_distribution(
        self,
        files: List[str],
        devices: List[str],
    ) -> Dict[str, List[str]]:
        if not devices:
            return {}
        num_devices = len(devices)
        chunk_size = len(files) // num_devices
        remainder = len(files) % num_devices
        distribution: Dict[str, List[str]] = {}
        cursor = 0
        for index, serial in enumerate(devices):
            count = chunk_size + (1 if index < remainder else 0)
            distribution[serial] = files[cursor : cursor + count]
            cursor += count
        return distribution

    def format_size(self, size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def total_size(self, src_dir: str, files: List[str]) -> int:
        total = 0
        for rel_path in files:
            abs_path = os.path.join(src_dir, rel_path)
            total += os.path.getsize(abs_path)
        return total
