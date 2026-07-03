"""Konfigurasi & value object dasar."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASE_URL = "https://siakad.pradita.ac.id"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class Credentials:
    """Kredensial login (value object)."""

    username: str
    password: str

    @classmethod
    def from_env(cls, env_path: Optional[Path] = None) -> "Credentials":
        load_dotenv(env_path or (PROJECT_ROOT / ".env"))
        username, password = os.getenv("USERNAME"), os.getenv("PASSWORD")
        if not username or not password:
            raise RuntimeError("USERNAME/PASSWORD tidak ditemukan di .env")
        return cls(username, password)


@dataclass(frozen=True)
class Semester:
    """Value object: tahun ajaran + tipe semester SIAKAD.

    tipe_semester: '1'=GANJIL, '2'=GENAP, '3'=SMT PENDEK.
    """

    tahun_ajaran: str
    tipe_semester: str

    _LABELS: ClassVar[dict] = {"1": "GANJIL", "2": "GENAP", "3": "SMT. PENDEK"}
    _CODES: ClassVar[dict] = {"PENDEK": "3", "GENAP": "2", "GANJIL": "1"}

    @classmethod
    def from_label(cls, label: str) -> "Semester":
        """'2025/2026 SMT. PENDEK' -> Semester('2025', '3')."""
        up = (label or "").upper()
        match = re.search(r"(\d{4})", up)
        tahun = match.group(1) if match else "2025"
        for key, code in cls._CODES.items():
            if key in up:
                return cls(tahun, code)
        return cls(tahun, "3")

    @property
    def label(self) -> str:
        berikut = str(int(self.tahun_ajaran) + 1) if self.tahun_ajaran.isdigit() else "?"
        return f"{self.tahun_ajaran}/{berikut} {self._LABELS.get(self.tipe_semester, '?')}"

    def as_json(self) -> str:
        """Bentuk JSON string untuk parameter 'tahun_akademik' di endpoint /search."""
        return json.dumps({"tahun_ajaran": self.tahun_ajaran, "tipe_semester": self.tipe_semester})
