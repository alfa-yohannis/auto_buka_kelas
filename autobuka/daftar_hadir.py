"""DaftarHadirService — akses data Daftar Hadir dosen (Repository/Service)."""
from __future__ import annotations

from typing import List

from .client import SiakadClient
from .config import Semester
from .models import ClassSession


class DaftarHadirService:
    """Membungkus endpoint /search dan /buka_kelas menjadi operasi domain."""

    SEARCH = "dosen/daftar_hadir/search"
    BUKA = "dosen/daftar_hadir/buka_kelas"

    def __init__(self, client: SiakadClient):
        self.client = client

    def search(self, semester: Semester, tanggal: str, text: str = "") -> List[ClassSession]:
        """Daftar pertemuan pada `tanggal` (YYYY-MM-DD) untuk `semester`.

        Meniru search_process() UI: sort_search='asc', order_search=2, page=1;
        tipe_semester/tahun_ajaran dikirim kosong, semester lewat 'tahun_akademik'.
        """
        data = {
            "page": 1,
            "sort_search": "asc",
            "order_search": 2,
            "text_search": text,
            "tipe_semester": "",
            "tahun_ajaran": "",
            "tanggal": tanggal,
            "tahun_akademik": semester.as_json(),
        }
        js = self.client.post_ajax(self.SEARCH, data).json()
        if js.get("error"):
            raise RuntimeError(f"search error dari server: {js.get('Message')}")
        rows = (js.get("rs_data") or {}).get("data") or []
        return [ClassSession.from_row(r) for r in rows]

    def buka(self, kelas: ClassSession) -> dict:
        """POST buka_kelas untuk satu pertemuan; kembalikan JSON respons."""
        resp = self.client.post_ajax(self.BUKA, kelas.buka_payload())
        try:
            return resp.json()
        except ValueError:
            return {"error": True, "Message": f"respons non-JSON: {resp.text[:200]}"}
