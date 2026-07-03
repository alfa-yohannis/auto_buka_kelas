#!/usr/bin/env python3
"""CLI interaktif: cari kelas, lalu buka sekarang (--open) atau tunggu T-15m (--wait).

    ./.venv/bin/python buka_kelas.py --text "Enterprise"              # cari (read-only)
    ./.venv/bin/python buka_kelas.py --text "Enterprise" --open --index 0
    ./.venv/bin/python buka_kelas.py --text "Enterprise" --wait --index 0
"""
from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone

from autobuka import (
    ClassOpener,
    Credentials,
    DaftarHadirService,
    Semester,
    ServerClock,
    SiakadClient,
    WIB,
    class_start,
)

OPEN_LEAD_MINUTES = 15


def show(rows):
    for i, k in enumerate(rows):
        status = f"SUDAH dibuka ({k.jam_absen})" if k.is_opened else "belum dibuka"
        print(f"[{i}] {k.nama}  ({k.kode})")
        print(f"     tgl={k.tgl_absensi} hari={k.hari} jam={k.start_hhmm} sesi={k.sesi} "
              f"ruang={k.ruang} dosen={k.dosen} -> {status}")


def pick(rows, index):
    if not rows:
        raise SystemExit("✗ Tidak ada baris.")
    if not 0 <= index < len(rows):
        raise SystemExit(f"✗ --index {index} di luar jangkauan (0..{len(rows) - 1}).")
    return rows[index]


def wait_until_window(client: SiakadClient, kelas, lead=OPEN_LEAD_MINUTES):
    clock = ServerClock(offset=client.server_time() - datetime.now(timezone.utc))
    start = class_start(kelas.tgl_absensi, kelas.jam_mulai_absensi)
    open_at = (start - timedelta(minutes=lead)).astimezone(timezone.utc)
    while True:
        now = clock.now_utc()
        remaining = (open_at - now).total_seconds()
        if remaining <= 3:
            return
        print(f"  menunggu… server={now.astimezone(WIB):%Y-%m-%d %H:%M:%S} WIB | "
              f"buka >= {open_at.astimezone(WIB):%H:%M:%S} WIB | sisa {int(remaining)}s", flush=True)
        time.sleep(min(max(remaining - 3, 1), 60))


def main() -> int:
    p = argparse.ArgumentParser(description="Cari & buka kelas di Daftar Hadir SIAKAD")
    p.add_argument("--tahun-ajaran", default="2025")
    p.add_argument("--tipe-semester", default="3", help="3=SMT PENDEK, 2=GENAP, 1=GANJIL")
    p.add_argument("--tanggal", default="2026-07-04", help="YYYY-MM-DD (filter tanggal)")
    p.add_argument("--text", default="", help="filter nama mata kuliah")
    p.add_argument("--index", type=int, default=0, help="baris ke- (0-based) yang dibuka")
    p.add_argument("--open", action="store_true", help="langsung coba buka sekarang")
    p.add_argument("--wait", action="store_true", help="tunggu T-15 menit lalu buka")
    p.add_argument("--poll", type=int, default=10)
    args = p.parse_args()

    creds = Credentials.from_env()
    client = SiakadClient()
    print("→ Login …")
    client.login(creds)
    service = DaftarHadirService(client)
    semester = Semester(args.tahun_ajaran, args.tipe_semester)

    print(f"→ Search: {semester.label} tanggal={args.tanggal} text={args.text or '(semua)'}")
    rows = service.search(semester, args.tanggal, text=args.text)
    print(f"✓ {len(rows)} baris\n")
    show(rows)

    if not (args.open or args.wait):
        print("\n(Read-only. Tambahkan --open atau --wait --index N.)")
        return 0

    kelas = pick(rows, args.index)
    opener = ClassOpener(service, retries=30 if args.wait else 1, poll=args.poll)

    if args.wait:
        print(f"\n→ Menunggu jendela buka '{kelas.nama}' (mulai {kelas.start_hhmm}) …")
        wait_until_window(client, kelas)
        print("→ Masuk jendela. Re-login & buka …")
        client.login(creds)
        rows = service.search(semester, args.tanggal, text=args.text)
        kelas = pick(rows, args.index)

    print(f"\n→ MEMBUKA [{args.index}] {kelas.nama} tgl={kelas.tgl_absensi} sesi={kelas.sesi} …")
    report = opener.open_session(kelas)
    if report.payload:
        print(f"  payload : {report.payload}")
    if report.response:
        print(f"  response: {report.response}")
    print(f"{'✓' if report.ok else '✗'} RESULT={report.status.value}: {report.message}")
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
