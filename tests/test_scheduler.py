import tempfile
import unittest
from pathlib import Path

from autobuka import CronScheduler

CSV = (
    "mata_kuliah,tanggal,waktu,ruang,program_studi,kelompok_kelas,semester\n"
    "Enterprise & Platform Architecture,07/04/2026,10:00 - 12:50,A201,Teknologi Informasi,-,2025/2026 SMT. PENDEK\n"
    "Pemrograman Berorientasi Objek,07/01/2026,08:25 - 10:10,A211 (Studio 3),Informatika,-,2025/2026 SMT. PENDEK\n"
)


class MemScheduler(CronScheduler):
    """CronScheduler dengan crontab di memori (tanpa subprocess)."""

    def __init__(self, store, **kw):
        super().__init__(**kw)
        self.store = store

    def read_crontab(self):
        return self.store.get("txt", "")

    def write_crontab(self, text):
        self.store["txt"] = text
        return True


class SchedulerTestBase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        tmp.write(CSV)
        tmp.close()
        self.csv = Path(tmp.name)
        self.addCleanup(self.csv.unlink)


class TestBuildBlock(SchedulerTestBase):
    def test_times_dow_and_flags(self):
        block = CronScheduler().build_block(self.csv)
        self.assertIn("CRON_TZ=Asia/Jakarta", block)
        self.assertIn("46 9 * * 6 ", block)   # Sabtu 10:00 -> buka 09:46
        self.assertIn("11 8 * * 3 ", block)   # Rabu 08:25 -> buka 08:11
        self.assertIn('--nama "Enterprise & Platform Architecture"', block)
        self.assertNotIn("--until", block)
        self.assertIn(CronScheduler.BEGIN, block)
        self.assertIn(CronScheduler.END, block)

    def test_job_fields(self):
        jobs = CronScheduler().jobs_from_csv(self.csv)
        self.assertEqual((jobs[0].minute, jobs[0].hour, jobs[0].dow), (46, 9, "6"))
        self.assertEqual((jobs[1].minute, jobs[1].hour, jobs[1].dow), (11, 8, "3"))


class TestStripAndInstall(SchedulerTestBase):
    def test_strip_managed(self):
        s = CronScheduler()
        text = "keep me\n" + s.build_block(self.csv) + "\nkeep too"
        stripped = s.strip_managed(text)
        self.assertIn("keep me", stripped)
        self.assertIn("keep too", stripped)
        self.assertNotIn(s.BEGIN, stripped)
        self.assertNotIn("46 9 * * 6", stripped)

    def test_install_idempotent_and_preserves_existing(self):
        store = {"txt": "0 5 * * 1 tar -zcf backup.tgz /home\n"}
        sched = MemScheduler(store)

        sched.install(self.csv)
        self.assertIn("0 5 * * 1 tar -zcf backup.tgz /home", store["txt"])
        self.assertEqual(store["txt"].count(CronScheduler.BEGIN), 1)

        sched.install(self.csv)  # dipasang lagi -> tetap satu blok
        self.assertEqual(store["txt"].count(CronScheduler.BEGIN), 1)
        self.assertIn("0 5 * * 1 tar -zcf backup.tgz /home", store["txt"])

    def test_remove_keeps_other_jobs(self):
        store = {"txt": "0 5 * * 1 tar -zcf backup.tgz /home\n"}
        sched = MemScheduler(store)
        sched.install(self.csv)
        sched.remove()
        self.assertNotIn(CronScheduler.BEGIN, store["txt"])
        self.assertIn("0 5 * * 1 tar -zcf backup.tgz /home", store["txt"])


if __name__ == "__main__":
    unittest.main()
