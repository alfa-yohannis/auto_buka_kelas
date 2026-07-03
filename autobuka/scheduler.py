"""CronScheduler — bangun & pasang jadwal crontab dari kelas.csv.

Logika murni (build_block, strip_managed, _job) dipisah dari I/O (read/write
crontab via subprocess) agar mudah diuji.
"""
from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from .config import PROJECT_ROOT, Semester
from .timeutil import parse_hhmm


@dataclass(frozen=True)
class CronJob:
    minute: int
    hour: int
    dow: str            # '%w' 0=Minggu..6=Sabtu
    command: str
    comment: str

    def line(self) -> str:
        return f"{self.minute} {self.hour} * * {self.dow} {self.command}"


class CronScheduler:
    BEGIN = "# >>> auto_buka_kelas (managed) >>>"
    END = "# <<< auto_buka_kelas (managed) <<<"

    def __init__(
        self,
        project_root: Path = PROJECT_ROOT,
        lead_minutes: int = 14,
        timezone: str = "Asia/Jakarta",
    ):
        self.root = Path(project_root)
        self.lead_minutes = lead_minutes
        self.timezone = timezone
        self.python = self.root / ".venv" / "bin" / "python"
        self.runner = self.root / "auto_buka.py"
        self.log = self.root / "tmp" / "cron.log"

    # -- logika murni -------------------------------------------------------
    def _job(self, row: dict) -> CronJob:
        nama = row["mata_kuliah"].strip()
        hour, minute = parse_hhmm(row["waktu"])
        tanggal = datetime.strptime(row["tanggal"].strip(), "%m/%d/%Y")  # MM/DD/YYYY
        semester = Semester.from_label(row.get("semester", ""))
        open_dt = datetime(2000, 1, 1, hour, minute) - timedelta(minutes=self.lead_minutes)
        jam = f"{hour:02d}:{minute:02d}"
        command = (
            f'cd {self.root} && {self.python} {self.runner} '
            f'--nama "{nama}" --jam "{jam}" '
            f'--tahun-ajaran {semester.tahun_ajaran} --tipe-semester {semester.tipe_semester} '
            f'>> {self.log} 2>&1'
        )
        comment = f"# {nama} — {tanggal.strftime('%A')} {jam} WIB (buka {open_dt:%H:%M})"
        return CronJob(open_dt.minute, open_dt.hour, tanggal.strftime("%w"), command, comment)

    def jobs_from_csv(self, csv_path: Path) -> List[CronJob]:
        with open(csv_path, newline="", encoding="utf-8") as f:
            return [self._job(row) for row in csv.DictReader(f)]

    def build_block(self, csv_path: Path) -> str:
        lines = [
            self.BEGIN,
            f"# auto dari {Path(csv_path).name} — buka {self.lead_minutes} menit sebelum jadwal, berulang tiap minggu",
            "SHELL=/bin/bash",
            f"CRON_TZ={self.timezone}",
        ]
        for job in self.jobs_from_csv(csv_path):
            lines.append(job.comment)
            lines.append(job.line())
        lines.append(self.END)
        return "\n".join(lines)

    def strip_managed(self, crontab_text: str) -> str:
        keep, skip = [], False
        for line in crontab_text.splitlines():
            if line.strip() == self.BEGIN:
                skip = True
                continue
            if line.strip() == self.END:
                skip = False
                continue
            if not skip:
                keep.append(line)
        return "\n".join(keep).rstrip("\n")

    def merged(self, existing: str, csv_path: Path) -> str:
        """Crontab baru = crontab lama (tanpa blok kita) + blok baru. Idempoten."""
        base = self.strip_managed(existing)
        block = self.build_block(csv_path)
        return (base + "\n\n" + block).lstrip("\n")

    # -- I/O (subprocess) — dioverride saat test ---------------------------
    def read_crontab(self) -> str:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else ""

    def write_crontab(self, text: str) -> bool:
        (self.root / "tmp").mkdir(exist_ok=True)
        (self.root / "tmp" / "crontab.backup").write_text(self.read_crontab())
        result = subprocess.run(["crontab", "-"], input=text.rstrip("\n") + "\n", text=True)
        return result.returncode == 0

    def install(self, csv_path: Path) -> str:
        block = self.build_block(csv_path)
        self.write_crontab(self.merged(self.read_crontab(), csv_path))
        return block

    def remove(self) -> bool:
        return self.write_crontab(self.strip_managed(self.read_crontab()))
