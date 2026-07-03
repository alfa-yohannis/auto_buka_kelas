"""Model domain: ClassSession (value object) + hasil operasi buka."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


@dataclass(frozen=True)
class ClassSession:
    """Satu pertemuan kelas, hasil parsing satu row dari endpoint /search.

    Catatan penting soal waktu:
      * jam_mulai_absensi (JAM_MULAI_ABSENSI) UNIK per sesi -> dipakai mencocokkan.
      * jam_mulai (JAM_MULAI) bisa SAMA antar sesi -> dikirim apa adanya di payload
        buka_kelas bersama `sesi` (persis seperti tombol di UI).
    """

    nama: str
    kode: str
    dosen_id: str
    tahun_ajaran: str
    tipe_semester: str
    hari: str
    jam_mulai: str
    jam_mulai_absensi: str
    tgl_absensi: str
    sesi: str
    ruang: str = ""
    prodi: str = ""
    kelompok: str = ""
    dosen: str = ""
    jam_absen: Optional[str] = None  # None = belum dibuka

    @classmethod
    def from_row(cls, row: dict) -> "ClassSession":
        def g(key: str) -> str:
            return (row.get(key) or "").strip()

        return cls(
            nama=g("NM_MATA_KULIAH"),
            kode=g("KD_MATA_KULIAH"),
            dosen_id=g("DOSEN_ID"),
            tahun_ajaran=g("TAHUN_AJARAN"),
            tipe_semester=g("TIPE_SEMESTER"),
            hari=g("HARI"),
            jam_mulai=g("JAM_MULAI"),
            jam_mulai_absensi=g("JAM_MULAI_ABSENSI"),
            tgl_absensi=g("TGL_ABSENSI"),
            sesi=g("SESI"),
            ruang=g("NM_RUANG"),
            prodi=g("NM_JURUSAN"),
            kelompok=g("KELOMPOK_KELAS"),
            dosen=g("NAMA_DOSEN"),
            jam_absen=(row.get("JAM_ABSEN") or None),
        )

    @property
    def is_opened(self) -> bool:
        return bool(self.jam_absen)

    @property
    def start_hhmm(self) -> str:
        """Jam mulai pertemuan 'HH:MM' (dari JAM_MULAI_ABSENSI)."""
        return (self.jam_mulai_absensi or "")[:5]

    def matches(self, nama: str, jam: str) -> bool:
        """Cocok bila nama persis sama dan jam mulai pertemuan sama."""
        return self.nama == (nama or "").strip() and self.start_hhmm == jam

    def buka_payload(self) -> dict:
        """8 field payload POST /buka_kelas (urut seperti onclick di UI)."""
        return {
            "dosen_id": self.dosen_id,
            "kd_mata_kuliah": self.kode,
            "tahun_ajaran": self.tahun_ajaran,
            "tipe_semester": self.tipe_semester,
            "hari": self.hari,
            "jam_mulai": self.jam_mulai,
            "tgl_absensi": self.tgl_absensi,
            "sesi": self.sesi,
        }


class OpenStatus(str, Enum):
    """Status hasil upaya membuka kelas (juga dipakai sebagai token log)."""

    BERHASIL = "BERHASIL"
    GAGAL = "GAGAL"
    SKIP = "SKIP"
    TANPA_COCOK = "TANPA-COCOK"
    ERROR = "ERROR"
    LEWAT_BATAS = "LEWAT-BATAS"


_EXIT_CODES = {
    OpenStatus.BERHASIL: 0,
    OpenStatus.SKIP: 0,
    OpenStatus.LEWAT_BATAS: 0,
    OpenStatus.TANPA_COCOK: 2,
}


@dataclass
class OpenReport:
    """Hasil satu operasi buka kelas."""

    status: OpenStatus
    message: str = ""
    session: Optional[ClassSession] = None
    payload: Optional[dict] = None
    response: Optional[dict] = None
    candidates: List[ClassSession] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status in (OpenStatus.BERHASIL, OpenStatus.SKIP)

    @property
    def exit_code(self) -> int:
        return _EXIT_CODES.get(self.status, 1)
