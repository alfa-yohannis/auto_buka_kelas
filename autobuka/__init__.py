"""Paket inti auto_buka_kelas.

Arsitektur (ringkas):
    SiakadClient        - Facade sesi HTTP + autentikasi (Laravel).
    DaftarHadirService  - Repository/Service: search & buka kelas.
    ClassSession        - Value object satu pertemuan kelas (+ factory from_row).
    Semester            - Value object tahun ajaran + tipe semester.
    ClassOpener         - Orkestrasi buka kelas (cari -> validasi -> buka + retry).
    OpenReport/OpenStatus - Hasil operasi buka (Enum).
    CronScheduler       - Membangun & memasang jadwal crontab dari kelas.csv.
    ServerClock/Clock   - Sumber waktu (Strategy, mudah di-mock saat test).
"""
from .client import HttpError, LoginError, SiakadClient
from .config import BASE_URL, PROJECT_ROOT, Credentials, Semester
from .daftar_hadir import DaftarHadirService
from .models import ClassSession, OpenReport, OpenStatus
from .opener import ClassOpener
from .scheduler import CronJob, CronScheduler
from .timeutil import WIB, Clock, ServerClock, class_start, parse_hhmm

__all__ = [
    "SiakadClient", "LoginError", "HttpError",
    "BASE_URL", "PROJECT_ROOT", "Credentials", "Semester",
    "DaftarHadirService", "ClassSession", "OpenReport", "OpenStatus",
    "ClassOpener", "CronJob", "CronScheduler",
    "WIB", "Clock", "ServerClock", "class_start", "parse_hhmm",
]
