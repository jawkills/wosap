from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple


class SettingsService:
    def __init__(
        self,
        settings_file: Path | None = None,
        labels_file: Path | None = None,
    ) -> None:
        self.settings_file = settings_file or Path("app_settings.json")
        self.labels_file = labels_file or Path("device_labels.json")
        self.default_destination_base = "//sdcard/XPersonal"
        self.default_destination_mode = "auto_date"

    def load_device_labels(self) -> Dict[str, str]:
        try:
            if self.labels_file.exists():
                with self.labels_file.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                    if isinstance(data, dict):
                        return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
        return {}

    def save_device_labels(self, labels: Dict[str, str]) -> None:
        with self.labels_file.open("w", encoding="utf-8") as handle:
            json.dump(labels, handle)

    def load_app_settings(self) -> Tuple[str, str]:
        destination_base = self.default_destination_base
        destination_mode = self.default_destination_mode

        try:
            if self.settings_file.exists():
                with self.settings_file.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                destination_base = str(data.get("destination_base", destination_base))
                destination_mode = str(data.get("destination_mode", destination_mode))
        except Exception:
            pass

        if destination_mode not in {"auto_date", "manual"}:
            destination_mode = self.default_destination_mode

        return destination_base, destination_mode

    def save_app_settings(self, destination_base: str, destination_mode: str) -> None:
        payload = {
            "destination_base": destination_base,
            "destination_mode": destination_mode,
        }
        with self.settings_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle)
