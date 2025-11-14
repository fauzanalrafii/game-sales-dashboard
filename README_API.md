Ini adalah petunjuk untuk menjalankan server API Anda.

### Latar Belakang

Aplikasi Streamlit Anda (`Home.py`) adalah "Toko" untuk Manusia. API (`api.py`) ini adalah "Gudang" untuk Mesin. Keduanya adalah server yang **berbeda** dan **berjalan terpisah**.

API ini **menduplikat** logika pembersihan data Anda karena tidak ada file `utils.py` untuk berbagi logika.

### Langkah 1: Instalasi Library Baru

Anda perlu 2 library baru untuk API. Buka terminal Anda dan jalankan:

```bash
# 1. FastAPI: Framework API-nya
pip install fastapi

# 2. Uvicorn: Server yang akan menjalankan API-nya
pip install "uvicorn[standard]"