import unittest

from autobuka import ClassSession, OpenReport, OpenStatus


def row(**kw):
    base = dict(
        NM_MATA_KULIAH="Pemrograman Berorientasi Objek",
        KD_MATA_KULIAH="IF30812",
        DOSEN_ID="0000245",
        TAHUN_AJARAN="2025",
        TIPE_SEMESTER="3",
        HARI="WEDNESDAY",
        JAM_MULAI="08:25:00.0000000",
        JAM_MULAI_ABSENSI="08:25:00.0000000",
        TGL_ABSENSI="2026-07-01",
        SESI="1",
        NM_RUANG="A211 (Studio 3)",
        NM_JURUSAN="Informatika",
        KELOMPOK_KELAS="-",
        NAMA_DOSEN="Alfa Ryano Yohannis",
        JAM_ABSEN=None,
    )
    base.update(kw)
    return base


class TestClassSession(unittest.TestCase):
    def test_from_row(self):
        k = ClassSession.from_row(row())
        self.assertEqual(k.nama, "Pemrograman Berorientasi Objek")
        self.assertEqual(k.kode, "IF30812")
        self.assertEqual(k.dosen_id, "0000245")
        self.assertEqual(k.sesi, "1")

    def test_is_opened(self):
        self.assertFalse(ClassSession.from_row(row()).is_opened)
        self.assertTrue(ClassSession.from_row(row(JAM_ABSEN="2026-07-01 08:23:06")).is_opened)

    def test_start_hhmm_uses_absensi(self):
        k = ClassSession.from_row(row(JAM_MULAI="08:25:00", JAM_MULAI_ABSENSI="13:55:00"))
        self.assertEqual(k.start_hhmm, "13:55")

    def test_matches_distinguishes_sessions(self):
        # Regresi: sesi 1 (08:25) & sesi 2 (13:55) punya JAM_MULAI sama.
        # Pembeda harus JAM_MULAI_ABSENSI, bukan JAM_MULAI.
        s1 = ClassSession.from_row(row(SESI="1", JAM_MULAI="08:25:00", JAM_MULAI_ABSENSI="08:25:00"))
        s2 = ClassSession.from_row(row(SESI="2", JAM_MULAI="08:25:00", JAM_MULAI_ABSENSI="13:55:00"))
        nama = "Pemrograman Berorientasi Objek"
        self.assertTrue(s1.matches(nama, "08:25"))
        self.assertFalse(s2.matches(nama, "08:25"))
        self.assertTrue(s2.matches(nama, "13:55"))

    def test_matches_exact_name(self):
        prakt = ClassSession.from_row(row(NM_MATA_KULIAH="Praktikum Pemrograman Berorientasi Objek"))
        self.assertFalse(prakt.matches("Pemrograman Berorientasi Objek", "08:25"))

    def test_buka_payload_uses_nominal_jam_mulai(self):
        k = ClassSession.from_row(row(SESI="2", JAM_MULAI="08:25:00.0000000", JAM_MULAI_ABSENSI="13:55:00"))
        payload = k.buka_payload()
        self.assertEqual(payload["jam_mulai"], "08:25:00.0000000")  # nominal, bukan absensi
        self.assertEqual(payload["sesi"], "2")
        self.assertEqual(
            set(payload),
            {"dosen_id", "kd_mata_kuliah", "tahun_ajaran", "tipe_semester",
             "hari", "jam_mulai", "tgl_absensi", "sesi"},
        )


class TestOpenReport(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(OpenReport(OpenStatus.BERHASIL).ok)
        self.assertTrue(OpenReport(OpenStatus.SKIP).ok)
        self.assertFalse(OpenReport(OpenStatus.GAGAL).ok)

    def test_exit_codes(self):
        self.assertEqual(OpenReport(OpenStatus.BERHASIL).exit_code, 0)
        self.assertEqual(OpenReport(OpenStatus.SKIP).exit_code, 0)
        self.assertEqual(OpenReport(OpenStatus.LEWAT_BATAS).exit_code, 0)
        self.assertEqual(OpenReport(OpenStatus.TANPA_COCOK).exit_code, 2)
        self.assertEqual(OpenReport(OpenStatus.GAGAL).exit_code, 1)
        self.assertEqual(OpenReport(OpenStatus.ERROR).exit_code, 1)


if __name__ == "__main__":
    unittest.main()
