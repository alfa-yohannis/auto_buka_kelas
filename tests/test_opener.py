import unittest

from autobuka import ClassOpener, ClassSession, OpenStatus, Semester

SEM = Semester("2025", "3")
NAMA = "Enterprise & Platform Architecture"
WINDOW_MSG = "Membuka kelas paling cepat hanya boleh 15 menit sebelum kelas dimulai."


def mk(nama=NAMA, jam="10:00:00", sesi="1", absen=None):
    return ClassSession.from_row(dict(
        NM_MATA_KULIAH=nama, KD_MATA_KULIAH="IT30812", DOSEN_ID="0000245",
        TAHUN_AJARAN="2025", TIPE_SEMESTER="3", HARI="SATURDAY",
        JAM_MULAI=jam, JAM_MULAI_ABSENSI=jam, TGL_ABSENSI="2026-07-04",
        SESI=sesi, JAM_ABSEN=absen,
    ))


class FakeService:
    def __init__(self, rows, buka_responses=None):
        self.rows = rows
        self.buka_responses = list(buka_responses or [])
        self.buka_calls = 0

    def search(self, semester, tanggal, text=""):
        return list(self.rows)

    def buka(self, kelas):
        self.buka_calls += 1
        if self.buka_responses:
            return self.buka_responses.pop(0)
        return {"error": False, "Message": "ok"}


class Sleeper:
    def __init__(self):
        self.count = 0

    def __call__(self, seconds):
        self.count += 1


class TestOpener(unittest.TestCase):
    def _open(self, svc, jam="10:00", **kw):
        return ClassOpener(svc, sleep=Sleeper(), **kw).open(SEM, "2026-07-04", NAMA, jam)

    def test_unique_match_opens(self):
        svc = FakeService([mk()], [{"error": False, "Message": "Kelas dibuka"}])
        report = self._open(svc)
        self.assertEqual(report.status, OpenStatus.BERHASIL)
        self.assertEqual(svc.buka_calls, 1)
        self.assertEqual(report.payload, mk().buka_payload())

    def test_already_opened_skips_without_calling_buka(self):
        svc = FakeService([mk(absen="2026-07-04 09:46:01")])
        report = self._open(svc)
        self.assertEqual(report.status, OpenStatus.SKIP)
        self.assertEqual(svc.buka_calls, 0)

    def test_no_match(self):
        svc = FakeService([mk(jam="09:00:00")])
        report = self._open(svc, jam="10:00")
        self.assertEqual(report.status, OpenStatus.TANPA_COCOK)
        self.assertEqual(len(report.candidates), 1)
        self.assertEqual(svc.buka_calls, 0)

    def test_ambiguous_two_matches(self):
        svc = FakeService([mk(sesi="1"), mk(sesi="2")])  # nama+jam sama
        report = self._open(svc)
        self.assertEqual(report.status, OpenStatus.TANPA_COCOK)
        self.assertEqual(svc.buka_calls, 0)

    def test_retry_then_success(self):
        svc = FakeService([mk()], [
            {"error": True, "Message": WINDOW_MSG},
            {"error": False, "Message": "Kelas dibuka"},
        ])
        sleeper = Sleeper()
        report = ClassOpener(svc, retries=3, poll=1, sleep=sleeper).open(SEM, "2026-07-04", NAMA, "10:00")
        self.assertEqual(report.status, OpenStatus.BERHASIL)
        self.assertEqual(svc.buka_calls, 2)
        self.assertEqual(sleeper.count, 1)

    def test_persistent_window_error_gives_gagal(self):
        svc = FakeService([mk()], [{"error": True, "Message": WINDOW_MSG} for _ in range(3)])
        sleeper = Sleeper()
        report = ClassOpener(svc, retries=3, poll=1, sleep=sleeper).open(SEM, "2026-07-04", NAMA, "10:00")
        self.assertEqual(report.status, OpenStatus.GAGAL)
        self.assertEqual(svc.buka_calls, 3)
        self.assertEqual(sleeper.count, 2)  # retry di antara 3 percobaan

    def test_non_window_error_no_retry(self):
        svc = FakeService([mk()], [{"error": True, "Message": "Kesalahan lain"}])
        sleeper = Sleeper()
        report = ClassOpener(svc, retries=3, poll=1, sleep=sleeper).open(SEM, "2026-07-04", NAMA, "10:00")
        self.assertEqual(report.status, OpenStatus.GAGAL)
        self.assertEqual(svc.buka_calls, 1)
        self.assertEqual(sleeper.count, 0)


if __name__ == "__main__":
    unittest.main()
