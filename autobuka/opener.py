"""ClassOpener — orkestrasi membuka satu kelas (cari -> validasi -> buka)."""
from __future__ import annotations

import time
from typing import Callable

from .config import Semester
from .daftar_hadir import DaftarHadirService
from .models import ClassSession, OpenReport, OpenStatus

# Penanda pesan server saat masih di luar jendela (mis. "...15 menit sebelum...").
WINDOW_HINT = "15 menit"


class ClassOpener:
    """Membuka satu kelas berdasarkan nama + jam mulai pertemuan.

    `sleep` di-inject agar retry dapat diuji tanpa menunggu sungguhan.
    """

    def __init__(
        self,
        service: DaftarHadirService,
        retries: int = 6,
        poll: int = 10,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.service = service
        self.retries = max(1, retries)
        self.poll = poll
        self._sleep = sleep

    def open(self, semester: Semester, tanggal: str, nama: str, jam: str) -> OpenReport:
        rows = self.service.search(semester, tanggal, text=nama)
        matches = [k for k in rows if k.matches(nama, jam)]

        if len(matches) != 1:
            return OpenReport(
                OpenStatus.TANPA_COCOK,
                f"{len(matches)} cocok dari {len(rows)} baris",
                candidates=rows,
            )

        return self.open_session(matches[0])

    def open_session(self, kelas: ClassSession) -> OpenReport:
        """Buka satu ClassSession yang sudah dipilih (skip bila sudah dibuka)."""
        if kelas.is_opened:
            return OpenReport(OpenStatus.SKIP, f"sudah dibuka pada {kelas.jam_absen}", session=kelas)
        return self._fire(kelas)

    def _fire(self, kelas: ClassSession) -> OpenReport:
        response: dict = {}
        for attempt in range(1, self.retries + 1):
            response = self.service.buka(kelas)
            if not response.get("error"):
                return OpenReport(
                    OpenStatus.BERHASIL, response.get("Message", ""),
                    session=kelas, payload=kelas.buka_payload(), response=response,
                )
            last_attempt = attempt >= self.retries
            if not last_attempt and WINDOW_HINT in (response.get("Message") or ""):
                self._sleep(self.poll)
                continue
            break

        return OpenReport(
            OpenStatus.GAGAL, response.get("Message", ""),
            session=kelas, payload=kelas.buka_payload(), response=response,
        )
