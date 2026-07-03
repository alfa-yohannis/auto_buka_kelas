import json
import unittest

from autobuka import ClassSession, DaftarHadirService, Semester


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class FakeClient:
    """Client palsu: memetakan path -> payload JSON, dan mencatat panggilan."""

    def __init__(self, by_path):
        self.by_path = by_path
        self.calls = []

    def post_ajax(self, path, data):
        self.calls.append((path, data))
        return FakeResp(self.by_path[path])


def a_row(nama="Enterprise & Platform Architecture", jam="10:00:00", sesi="1", absen=None):
    return dict(
        NM_MATA_KULIAH=nama, KD_MATA_KULIAH="IT30812", DOSEN_ID="0000245",
        TAHUN_AJARAN="2025", TIPE_SEMESTER="3", HARI="SATURDAY",
        JAM_MULAI=jam, JAM_MULAI_ABSENSI=jam, TGL_ABSENSI="2026-07-04",
        SESI=sesi, JAM_ABSEN=absen,
    )


class TestSearch(unittest.TestCase):
    def test_parses_rows_and_sends_expected_params(self):
        client = FakeClient({DaftarHadirService.SEARCH: {"rs_data": {"data": [a_row(), a_row(sesi="2")]}}})
        rows = DaftarHadirService(client).search(Semester("2025", "3"), "2026-07-04", text="Ent")

        self.assertEqual(len(rows), 2)
        self.assertIsInstance(rows[0], ClassSession)

        path, data = client.calls[0]
        self.assertEqual(path, DaftarHadirService.SEARCH)
        self.assertEqual(data["sort_search"], "asc")
        self.assertEqual(data["order_search"], 2)
        self.assertEqual(data["tanggal"], "2026-07-04")
        self.assertEqual(data["text_search"], "Ent")
        self.assertEqual(data["tipe_semester"], "")
        self.assertEqual(data["tahun_ajaran"], "")
        self.assertEqual(json.loads(data["tahun_akademik"]),
                         {"tahun_ajaran": "2025", "tipe_semester": "3"})

    def test_empty(self):
        client = FakeClient({DaftarHadirService.SEARCH: {"rs_data": {"data": []}}})
        self.assertEqual(DaftarHadirService(client).search(Semester("2025", "3"), "2026-07-04"), [])

    def test_server_error_raises(self):
        client = FakeClient({DaftarHadirService.SEARCH: {"error": True, "Message": "boom"}})
        with self.assertRaises(RuntimeError):
            DaftarHadirService(client).search(Semester("2025", "3"), "2026-07-04")


class TestBuka(unittest.TestCase):
    def test_sends_payload(self):
        client = FakeClient({DaftarHadirService.BUKA: {"error": False, "Message": "Kelas dibuka"}})
        kelas = ClassSession.from_row(a_row(sesi="2"))
        resp = DaftarHadirService(client).buka(kelas)

        self.assertFalse(resp["error"])
        path, data = client.calls[0]
        self.assertEqual(path, DaftarHadirService.BUKA)
        self.assertEqual(data, kelas.buka_payload())


if __name__ == "__main__":
    unittest.main()
