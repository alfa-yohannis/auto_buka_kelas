import json
import unittest

from autobuka import Semester


class TestSemester(unittest.TestCase):
    def test_from_label_pendek(self):
        s = Semester.from_label("2025/2026 SMT. PENDEK")
        self.assertEqual((s.tahun_ajaran, s.tipe_semester), ("2025", "3"))

    def test_from_label_genap(self):
        self.assertEqual(Semester.from_label("2024 / 2025 GENAP").tipe_semester, "2")

    def test_from_label_ganjil(self):
        self.assertEqual(Semester.from_label("2023 / 2024 GANJIL").tipe_semester, "1")

    def test_from_label_default_pendek(self):
        self.assertEqual(Semester.from_label("tak dikenal").tipe_semester, "3")

    def test_label_roundtrip(self):
        self.assertEqual(Semester("2025", "3").label, "2025/2026 SMT. PENDEK")

    def test_as_json(self):
        self.assertEqual(
            json.loads(Semester("2025", "3").as_json()),
            {"tahun_ajaran": "2025", "tipe_semester": "3"},
        )


if __name__ == "__main__":
    unittest.main()
