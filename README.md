# auto_buka_kelas

Otomasi **login SIAKAD Pradita** dan **buka kelas (Daftar Hadir dosen)** secara
terprogram dengan Python, lalu menjadwalkannya lewat **cron** agar tiap kelas
dibuka otomatis **14 menit sebelum** jadwal, **berulang tiap minggu**.

> Status: login, cari, & buka kelas jalan + teruji (**36 unit test**). Kode
> ditata sebagai paket OOP [`autobuka/`](#arsitektur-paket-autobuka). Jadwal cron
> terpasang (5 kelas, mingguan, zona `Asia/Jakarta`). Buka kelas dijaga
> **server-side** (min. 15 menit sebelum mulai) — lihat
> [Temuan penting](#-temuan-penting-wajib-baca).

---

## ⚠️ Temuan penting (WAJIB BACA)

Tombol **"Buka"** dijaga **dua lapis**:

1. **UI (client-side)** — JS memberi atribut `disabled` kalau bukan hari-H atau
   sudah dibuka. Hanya cosmetic; bisa "dilewati" dengan memanggil endpoint
   langsung (script ini).
2. **Server-side** — `POST /dosen/daftar_hadir/buka_kelas` **tetap** menolak di
   luar waktu:
   > `Membuka kelas paling cepat hanya boleh 15 menit sebelum kelas dimulai.`

**Konsekuensi:** tidak ada cara "menipu" tanpa **memalsukan** `jam_mulai`/
`tgl_absensi` (TIDAK dilakukan). Maka auto-buka = menembak request **asli** pada
**T-14 menit** (aman: 14 < 15, sudah di dalam jendela). Itulah yang dilakukan cron.

---

## Setup

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt      # requests, python-dotenv, beautifulsoup4
```

`.env` (gitignored):

```env
USERNAME=alfa.ryano@pradita.ac.id
PASSWORD=xxxxxxxx
```

---

## Struktur file

| Path | Guna |
|------|------|
| [`autobuka/`](autobuka/) | **Paket inti (OOP)** — semua logika: client, service, model, opener, scheduler. Lihat [Arsitektur](#arsitektur-paket-autobuka). |
| [siakad.py](siakad.py) | CLI tipis: login + simpan `tmp/daftar_hadir.html`. |
| [buka_kelas.py](buka_kelas.py) | CLI tipis interaktif: cari kelas + buka (`--open` / `--wait`). |
| [auto_buka.py](auto_buka.py) | CLI tipis **dipanggil cron**: buka SATU kelas terjadwal + logging. |
| [install_cron.py](install_cron.py) | CLI tipis: pasang/copot jadwal cron dari `kelas.csv`. |
| [tests/](tests/) | **Unit test** (stdlib `unittest`) — 36 test, tanpa jaringan. |
| [kelas.csv](kelas.csv) | Daftar kelas (mata kuliah, tanggal, jam, ruang, prodi, kelompok, semester). |
| [requirements.txt](requirements.txt) | Dependency. |
| `.env` | Kredensial (gitignored). |
| `tmp/` | Dump HTML/JSON, **log** (`auto_buka.log`, `cron.log`), `crontab.backup` (gitignored). |

---

## A. Cara menjalankan MANUAL

Semua dari root repo memakai interpreter venv (`./.venv/bin/python`).

### 1. Cari / lihat kelas (read-only, aman)

```bash
./.venv/bin/python buka_kelas.py --text "Enterprise"      # filter nama
./.venv/bin/python buka_kelas.py --tanggal 2026-07-01     # semua kelas tanggal itu
./.venv/bin/python buka_kelas.py --tanggal 2026-07-04 --tahun-ajaran 2025 --tipe-semester 3
```

Hasil lengkap → `tmp/search_result.json`.

### 2. Buka SATU kelas sekarang (langsung; hanya berhasil bila di dalam jendela 15 menit)

```bash
# a) via buka_kelas.py — pilih baris hasil search dengan --index
./.venv/bin/python buka_kelas.py --text "Enterprise" --open --index 0

# b) via auto_buka.py — identifikasi pakai nama + jam mulai pertemuan (JAM_MULAI_ABSENSI)
./.venv/bin/python auto_buka.py --nama "Enterprise & Platform Architecture" --jam "10:00"
```

> Di luar jendela, server balas `"…15 menit sebelum kelas dimulai."` (lihat log).

### 3. Tunggu otomatis sampai jendela buka, lalu tembak (satu proses)

```bash
# tidur sampai T-15m (sinkron jam server), lalu buka; tahan tutup terminal:
nohup ./.venv/bin/python buka_kelas.py --text "Enterprise" --wait > tmp/auto.log 2>&1 &
tail -f tmp/auto.log
```

### 4. Uji persis seperti yang dijalankan cron

```bash
# meniru entri cron kelas Rabu 08:25 (pakai --tanggal untuk uji tanggal lampau)
./.venv/bin/python auto_buka.py --nama "Pemrograman Berorientasi Objek" --jam "08:25" --tanggal 2026-07-01
```

Ringkas opsi `auto_buka.py`: `--nama` (persis `NM_MATA_KULIAH`), `--jam` (jam
mulai pertemuan HH:MM), `--tanggal` (default: hari ini), `--tahun-ajaran`,
`--tipe-semester`, `--retries`, `--poll`, `--until` (opsional; default tanpa batas).

---

## B. Otomatis via CRON (sudah terpasang)

```bash
./.venv/bin/python install_cron.py            # PREVIEW (tidak mengubah apa pun)
./.venv/bin/python install_cron.py --install  # pasang / perbarui blok
./.venv/bin/python install_cron.py --remove   # copot blok
crontab -l                                     # lihat crontab aktif
```

- Membaca `kelas.csv`, membuat **1 entri per baris**, **mingguan** (hari diambil
  dari tanggal), memicu `auto_buka.py` **14 menit sebelum** jam mulai.
- Timezone dipaksa `CRON_TZ=Asia/Jakarta`. Idempoten (blok bertanda
  `# >>> auto_buka_kelas (managed) >>>`), **tidak mengganggu** cron job lain.
- **Menambah/ubah kelas:** edit `kelas.csv`, lalu `install_cron.py --install` lagi.

Jadwal yang terpasang saat ini:

| Kelas | Hari | Mulai | Cron buka (WIB) |
|-------|------|-------|-----------------|
| Enterprise & Platform Architecture | Sabtu | 10:00 | 09:46 — `46 9 * * 6` |
| Pemrograman Berorientasi Objek (sesi 1) | Rabu | 08:25 | 08:11 — `11 8 * * 3` |
| Pemrograman Berorientasi Objek (sesi 2) | Rabu | 13:55 | 13:41 — `41 13 * * 3` |
| Praktikum Pemrograman Berorientasi Objek (sesi 1) | Rabu | 10:15 | 10:01 — `1 10 * * 3` |
| Praktikum Pemrograman Berorientasi Objek (sesi 2) | Rabu | 15:45 | 15:31 — `31 15 * * 3` |

---

## Log — cek berhasil / tidaknya

- **`tmp/auto_buka.log`** — terstruktur, satu blok per eksekusi, ada baris `RESULT=`.
- **`tmp/cron.log`** — stdout/stderr mentah dari cron (cadangan).

```bash
tail -f tmp/auto_buka.log
grep "RESULT=" tmp/auto_buka.log        # ringkas status semua run
```

Nilai `RESULT=`:

| Token | Arti |
|-------|------|
| `BERHASIL` | Kelas berhasil dibuka. |
| `GAGAL` | Ditolak server (mis. di luar jendela 15 menit) — pesan asli disertakan. |
| `SKIP` | Kelas sudah dibuka sebelumnya (`JAM_ABSEN` terisi). |
| `TANPA-COCOK` | Tidak ada / lebih dari satu baris cocok (kandidat di-log). |
| `ERROR` | Login/koneksi/search gagal. |
| `LEWAT-BATAS` | Hanya jika `--until` dipakai dan tanggal sudah lewat. |

Contoh (dari uji nyata):

```
… RESULT=SKIP 'Pemrograman Berorientasi Objek' jam=08:25 sesi=1 sudah dibuka pada 2026-07-01 08:23:06.217
… RESULT=GAGAL 'Enterprise & Platform Architecture' jam=10:00 sesi=1: Membuka kelas paling cepat hanya boleh 15 menit sebelum kelas dimulai.
```

---

## Arsitektur (paket `autobuka/`)

Semua logika ada di paket `autobuka/`; keempat file CLI di root hanya *thin
wrapper* yang merangkai objek-objek ini. Argumen CLI tidak berubah, jadi crontab
yang sudah terpasang tetap aman.

| Modul / kelas | Peran | Pola |
|---------------|-------|------|
| `client.SiakadClient` | Bungkus `requests.Session` + login + CSRF + header AJAX. | **Facade** |
| `daftar_hadir.DaftarHadirService` | Operasi domain `search()` & `buka()`. | **Repository/Service** |
| `models.ClassSession` | Satu pertemuan kelas; `from_row()`, `matches()`, `buka_payload()`. | **Value Object + Factory Method** |
| `config.Semester`, `config.Credentials` | Semester & kredensial `.env`. | **Value Object** |
| `opener.ClassOpener` | Orkestrasi cari → validasi → buka (+ retry). `service` & `sleep` di-*inject*. | **Dependency Injection** |
| `timeutil.Clock` / `ServerClock` | Sumber waktu (sinkron jam server), mudah di-mock. | **Strategy** |
| `models.OpenStatus` / `OpenReport` | Hasil operasi buka (status + `exit_code`). | **Enum + Result object** |
| `scheduler.CronScheduler` | Bangun/pasang/copot blok crontab dari CSV; logika murni dipisah dari I/O. | — |

Alur khas (dipakai `auto_buka.py`):

```python
from autobuka import ClassOpener, Credentials, DaftarHadirService, Semester, SiakadClient

client = SiakadClient()
client.login(Credentials.from_env())
opener = ClassOpener(DaftarHadirService(client))
report = opener.open(Semester("2025", "3"), "2026-07-04",
                     "Enterprise & Platform Architecture", "10:00")
print(report.status, report.message)   # OpenStatus.BERHASIL / GAGAL / SKIP / ...
```

## Menjalankan test

```bash
./.venv/bin/python -m unittest discover -s tests -t .        # semua (36 test)
./.venv/bin/python -m unittest discover -s tests -t . -v     # verbose
./.venv/bin/python -m unittest tests.test_opener             # satu modul
```

Test memakai stdlib `unittest` (tanpa dependency tambahan) dan **tidak menyentuh
jaringan** — `SiakadClient`/`DaftarHadirService` diganti *fake*. Cakupan:

- `test_config` — parsing `Semester` (label ↔ kode, JSON).
- `test_timeutil` — `parse_hhmm`, `class_start`, offset `ServerClock`.
- `test_models` — `ClassSession.from_row`, **regresi** pembeda sesi lewat `JAM_MULAI_ABSENSI`, payload pakai `JAM_MULAI` nominal.
- `test_daftar_hadir` — parameter `/search` & payload `/buka_kelas` (fake client).
- `test_opener` — unik / skip / tanpa-cocok / ambigu + retry (sleep di-inject, tanpa menunggu).
- `test_scheduler` — waktu & hari cron, idempotensi, tidak mengganggu job lain.

---

## Referensi teknis (untuk melanjutkan)

Backend **Laravel** (cookie `XSRF-TOKEN` + `siakad_session`, field `_token`,
`<meta name="csrf-token">`).

### Login

1. `GET /login` → scrape `_token` (atau `meta csrf-token`) + cookie sesi.
2. `POST /login_process`: `_token`, `email` (=`USERNAME`), `password`, `remember_me=on`.
3. Sukses → `302 /dashboard`; gagal → balik `/login`.

### Endpoint (dari `tmp/daftar_hadir.html`)

| Endpoint | Method | Guna |
|----------|--------|------|
| `/login`, `/login_process` | GET/POST | Login. |
| `/dosen/daftar_hadir` | GET | Halaman (ada `meta csrf-token`). |
| `/dosen/daftar_hadir/search` | POST | Daftar kelas (JSON). |
| `/dosen/daftar_hadir/buka_kelas` | POST | **Buka kelas** (dijaga 15 menit server-side). |
| `/dosen/daftar_hadir/detail` | POST | Detail / daftar mahasiswa. |
| `/dosen/daftar_hadir/save` | POST | Simpan kehadiran. |
| `/dosen/daftar_hadir/save_pembahasan` | POST | Simpan pembahasan. |
| `/dosen/daftar_hadir/upload_kehadiran` | POST | Upload kehadiran. |

Semua AJAX butuh header `X-CSRF-TOKEN` + `X-Requested-With: XMLHttpRequest` + cookie sesi.

### `POST /search` — payload

```
page=1  sort_search=asc  order_search=2  text_search=<nama>
tipe_semester=  tahun_ajaran=            (KOSONG)
tanggal=YYYY-MM-DD
tahun_akademik={"tahun_ajaran":"2025","tipe_semester":"3"}   (JSON string)
```

> `sort_search`/`order_search` **wajib** valid (kosong → **500**). Semester
> diambil server dari `tahun_akademik`, bukan dari `tipe_semester`/`tahun_ajaran`.

### `POST /buka_kelas` — payload (8 field dari `row`)

```
dosen_id, kd_mata_kuliah, tahun_ajaran, tipe_semester, hari, jam_mulai, tgl_absensi, sesi
```

### ⚠️ Gotcha waktu (penting untuk identifikasi kelas)

- **`JAM_MULAI_ABSENSI`** = jam mulai pertemuan **sebenarnya**, **beda tiap sesi**
  (PBO sesi 1 = 08:25, sesi 2 = 13:55). → **dipakai untuk mencocokkan** kelas
  (`auto_buka.py --jam`).
- **`JAM_MULAI`** = jam nominal, bisa **sama** untuk beberapa sesi. → dikirim
  **apa adanya** di payload `buka_kelas` bersama `SESI` (persis seperti tombol UI).
- Kunci unik satu pertemuan = `NM_MATA_KULIAH` + `JAM_MULAI_ABSENSI` (+ `SESI`).

### Field pada `row` hasil `/search`

`DOSEN_ID, KD_MATA_KULIAH, TAHUN_AJARAN, TIPE_SEMESTER, HARI, JAM_MULAI,
JAM_MULAI_ABSENSI, JAM_SELESAI(_ABSENSI), TGL_ABSENSI, SESI, NM_MATA_KULIAH,
NM_RUANG, NM_JURUSAN, KELOMPOK_KELAS, NAMA_DOSEN, JAM_ABSEN` (`null`=belum dibuka).

---

## Data kelas (lihat `kelas.csv`)

Semester **2025/2026 SMT. PENDEK** (`tahun_ajaran=2025`, `tipe_semester=3`).
Semua milik **Alfa Ryano Yohannis** (DOSEN_ID `0000245`).

| Mata kuliah | Kode | Hari | Jam | Ruang | Prodi |
|-------------|------|------|-----|-------|-------|
| Enterprise & Platform Architecture | IT30812 | Sabtu | 10:00–12:50 | A201 | Teknologi Informasi |
| Pemrograman Berorientasi Objek | IF30812 | Rabu | 08:25–10:10 | A211 (Studio 3) | Informatika |
| Pemrograman Berorientasi Objek | IF30812 | Rabu | 13:55–15:40 | A211 (Studio 3) | Informatika |
| Praktikum Pemrograman Berorientasi Objek | IF30821 | Rabu | 10:15–12:00 | A211 (Studio 3) | Informatika |
| Praktikum Pemrograman Berorientasi Objek | IF30821 | Rabu | 15:45–17:30 | A211 (Studio 3) | Informatika |

---

## Langkah berikutnya (ide)

- [ ] Verifikasi end-to-end saat jendela nyata (mis. Sabtu ±09:46 untuk Enterprise)
      → cek `grep RESULT= tmp/auto_buka.log` menampilkan `BERHASIL`.
- [ ] Otomasi isi kehadiran setelah kelas terbuka via `/detail` + `/save`.
- [ ] Tambah kelas baru: cukup edit `kelas.csv` lalu `install_cron.py --install`.

## Catatan etis

Mengotomasi aksi **sah** dosen atas **kelas & akun sendiri**. Aturan 15 menit
server **dihormati** (jalan di T-14, bukan dipalsukan). Jangan menambahkan
pemalsuan `jam_mulai`/`tgl_absensi`.
