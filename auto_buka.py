#!/usr/bin/env python3
"""CLI (dipanggil cron): buka SATU kelas terjadwal + logging jelas berhasil/tidak.

Kelas diidentifikasi dari --nama (NM_MATA_KULIAH persis) + --jam (jam mulai
pertemuan HH:MM = JAM_MULAI_ABSENSI). Log ke tmp/auto_buka.log (cari `RESULT=`).

    ./.venv/bin/python auto_buka.py --nama "Enterprise & Platform Architecture" --jam "10:00"
"""
from __future__ import annotations

import argparse
import logging

from autobuka import (
    ClassOpener,
    Credentials,
    DaftarHadirService,
    OpenReport,
    OpenStatus,
    PROJECT_ROOT,
    Semester,
    SiakadClient,
    WIB,
)

LOGFILE = PROJECT_ROOT / "tmp" / "auto_buka.log"


def setup_logging() -> logging.Logger:
    (PROJECT_ROOT / "tmp").mkdir(exist_ok=True)
    logger = logging.getLogger("auto_buka")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(message)s", "%Y-%m-%d %H:%M:%S %z")
    for handler in (logging.FileHandler(LOGFILE, encoding="utf-8"), logging.StreamHandler()):
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    return logger


def log_report(log: logging.Logger, report: OpenReport) -> None:
    if report.payload:
        log.info(f"payload  = {report.payload}")
    if report.response:
        log.info(f"response = {report.response}")
    if report.status is OpenStatus.TANPA_COCOK:
        for c in report.candidates:
            log.warning(
                f"  kandidat: {c.nama!r} jam_absensi={c.start_hhmm} "
                f"jam_mulai={c.jam_mulai[:5]} sesi={c.sesi} dibuka={c.jam_absen}"
            )
    sesi = f" sesi={report.session.sesi}" if report.session else ""
    line = f"RESULT={report.status.value}{sesi}: {report.message}"
    if report.ok:
        log.info(line)
    elif report.status in (OpenStatus.GAGAL, OpenStatus.ERROR):
        log.error(line)
    else:
        log.warning(line)


def main() -> int:
    p = argparse.ArgumentParser(description="Buka satu kelas terjadwal (dipanggil cron)")
    p.add_argument("--nama", required=True, help="NM_MATA_KULIAH persis")
    p.add_argument("--jam", required=True, help="jam mulai pertemuan HH:MM (= JAM_MULAI_ABSENSI)")
    p.add_argument("--tanggal", default=None, help="default: hari ini (jam server)")
    p.add_argument("--tahun-ajaran", default="2025")
    p.add_argument("--tipe-semester", default="3")
    p.add_argument("--until", default=None, help="opsional; batas akhir YYYY-MM-DD (inklusif)")
    p.add_argument("--retries", type=int, default=6)
    p.add_argument("--poll", type=int, default=10)
    args = p.parse_args()

    log = setup_logging()
    label = f"{args.nama!r} jam={args.jam}"
    log.info(f"===== MULAI: {label} tanggal={args.tanggal or 'hari-ini'} until={args.until} =====")

    try:
        client = SiakadClient()
        client.login(Credentials.from_env())
        now_wib = client.server_time().astimezone(WIB)
    except Exception as exc:  # noqa: BLE001 — cron harus mencatat kegagalan apa pun
        log.error(f"RESULT=ERROR login/koneksi gagal: {exc!r}")
        return 1

    tanggal = args.tanggal or now_wib.strftime("%Y-%m-%d")
    log.info(f"jam server = {now_wib:%Y-%m-%d %H:%M:%S} WIB | tanggal cari = {tanggal}")

    if args.until and tanggal > args.until:
        log.warning(f"RESULT=LEWAT-BATAS tgl={tanggal} > until={args.until}; tidak membuka.")
        return 0

    semester = Semester(args.tahun_ajaran, args.tipe_semester)
    opener = ClassOpener(DaftarHadirService(client), retries=args.retries, poll=args.poll)
    try:
        report = opener.open(semester, tanggal, args.nama, args.jam)
    except Exception as exc:  # noqa: BLE001
        log.error(f"RESULT=ERROR saat buka: {exc!r}")
        return 1

    log_report(log, report)
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
