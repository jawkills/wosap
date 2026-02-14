# Wosap

Wosap adalah aplikasi desktop Windows untuk mendistribusikan file `.tar.gz` ke banyak perangkat Android menggunakan ADB.

## Fitur Utama

- UI desktop berbasis PySide6 (tema terang, layout compact)
- Scan file `.tar.gz` secara rekursif dari folder sumber
- Pilih perangkat tertentu (bisa pilih semua / hapus semua)
- Label nama perangkat custom (disimpan otomatis)
- Mode tujuan:
  - Otomatis berdasarkan tanggal (`YYYYMMDD`)
  - Manual full path
- Preview distribusi sebelum proses dimulai
- Transfer paralel multi-device
- Pause / lanjut proses transfer
- Status per-perangkat + log detail
- Jika satu perangkat gagal, perangkat lain tetap lanjut

## Persyaratan

- Windows
- Python 3.12+
- ADB (Android Platform Tools) tersedia di `PATH`

Cek ADB:

```bash
adb version
adb devices
```

## Jalankan dari Source

```bash
python -m pip install -r requirements.txt
python wosap.py
```

## Build EXE

```bash
build.bat
```

Hasil build:
- `dist/Wosap/Wosap.exe`

## Build Installer (Setup EXE)

Pastikan **Inno Setup 6** sudah terpasang, lalu jalankan:

```bash
build-installer.bat
```

Hasil build installer:
- `installer/Wosap-Setup-1.0.1.exe`

## Rilis GitHub

Rilis terbaru tersedia di:
- `https://github.com/jawkills/wosap/releases/tag/v1.0.1`

Asset installer langsung:
- `https://github.com/jawkills/wosap/releases/download/v1.0.1/Wosap-Setup-1.0.1.exe`

## Cara Share ke User

Yang dibagikan (disarankan):
- file installer `Wosap-Setup-1.0.1.exe`

Instruksi singkat untuk user:
1. Jalankan installer.
2. Klik Next -> Install -> Finish.
3. Buka Wosap dari Desktop/Start Menu.
4. Pastikan ADB sudah terpasang dan bisa dipanggil dari CMD.

## Troubleshooting Singkat

- **Perangkat tidak terdeteksi**
  - Cek kabel/data mode
  - Jalankan `adb devices`
  - Aktifkan USB debugging

- **Aplikasi tidak bisa transfer**
  - Pastikan path folder sumber valid
  - Pastikan minimal 1 perangkat dipilih
  - Cek log aplikasi untuk detail error

- **Windows SmartScreen muncul**
  - Klik **More info** -> **Run anyway** (jika sumber file terpercaya)
