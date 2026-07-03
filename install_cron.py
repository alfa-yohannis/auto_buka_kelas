#!/usr/bin/env python3
"""CLI: pasang/copot jadwal auto-buka ke crontab dari kelas.csv.

    ./.venv/bin/python install_cron.py            # preview (tidak mengubah apa pun)
    ./.venv/bin/python install_cron.py --install  # pasang / perbarui blok
    ./.venv/bin/python install_cron.py --remove   # copot blok terkelola
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from autobuka import CronScheduler, PROJECT_ROOT


def main() -> int:
    ap = argparse.ArgumentParser(description="Pasang jadwal auto-buka ke crontab")
    ap.add_argument("--csv", default=str(PROJECT_ROOT / "kelas.csv"))
    ap.add_argument("--install", action="store_true", help="pasang / perbarui ke crontab")
    ap.add_argument("--remove", action="store_true", help="copot blok terkelola")
    args = ap.parse_args()

    scheduler = CronScheduler()

    if args.remove:
        ok = scheduler.remove()
        print("✓ Blok auto_buka_kelas dicopot." if ok else "✗ Gagal mengubah crontab.",
              file=sys.stderr)
        return 0 if ok else 1

    block = scheduler.build_block(Path(args.csv))
    print(block)

    if not args.install:
        print("\n# (preview) tambahkan --install untuk memasang ke crontab", file=sys.stderr)
        return 0

    scheduler.install(Path(args.csv))
    print("\n✓ crontab terpasang (backup: tmp/crontab.backup). Cek: crontab -l", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
