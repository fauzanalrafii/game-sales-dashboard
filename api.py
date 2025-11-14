import pandas as pd
import numpy as np
from fastapi import FastAPI, Query
import json # <-- TAMBAHAN BARU

# --- 1. DUPLIKASI LOGIKA PEMBERSIHAN DATA ---
# (Logika ini kita salin dari file 'pages' Anda)
def get_clean_data_for_api(file_path):
    """
    Memuat dan membersihkan data CSV vgchartz.
    Ini adalah fungsi MURNI (pure) tanpa Streamlit.
    """
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' tidak ditemukan.")
        return None
    
    # 1. Filter krusial
    df_clean = df.dropna(subset=['total_sales']).copy()
    
    # 2. Pembersihan Tanggal
    df_clean['release_date'] = pd.to_datetime(df_clean['release_date'], errors='coerce')
    df_clean['release_year'] = df_clean['release_date'].dt.year
    df_clean['release_year'] = df_clean['release_year'].fillna(0).astype(int)
    
    # 3. Pembersihan Regional
    regional_cols = ['na_sales', 'jp_sales', 'pal_sales', 'other_sales']
    df_clean[regional_cols] = df_clean[regional_cols].fillna(0)
    
    # 4. Pembersihan Kategori
    df_clean['genre'] = df_clean['genre'].fillna('Unknown')
    df_clean['console'] = df_clean['console'].fillna('Unknown')
    
    # 5. Pembersihan Skor Kritikus (mengubah 0.0 menjadi NaN)
    df_clean['critic_score'] = df_clean['critic_score'].replace(0.0, np.nan)
    
    return df_clean

# --- 2. Inisialisasi Aplikasi FastAPI ---
app = FastAPI(
    title="Game Sales API",
    description="API untuk mendapatkan data penjualan game yang sudah dibersihkan dari vgchartz.",
    version="1.0.0"
)

# --- 3. Memuat Data Saat Startup ---
print("Memuat dan membersihkan data untuk API...")
try:
    df_clean = get_clean_data_for_api("vgchartz-2024.csv")
    if df_clean is None:
        raise RuntimeError("Gagal memuat file CSV. Pastikan 'vgchartz-2024.csv' ada.")
    print("Data berhasil dimuat dan dibersihkan untuk API.")
except Exception as e:
    print(f"FATAL ERROR saat startup: {e}")
    df_clean = pd.DataFrame() 

# --- 4. Mendefinisikan Endpoint (URL) ---

@app.get("/")
def read_root():
    """
    Endpoint utama. Memberi salam dan info.
    """
    return {
        "message": "Selamat datang di Game Sales API!",
        "documentation": "/docs",
        "endpoints": {
            "/games/all": "Mendapatkan semua game (limit 1000).",
            "/games/top": "Mendapatkan game Top N terlaris.",
            "/games/search": "Mencari game berdasarkan judul."
        }
    }

@app.get("/games/all")
def get_all_games(limit: int = 1000):
    """
    Mendapatkan semua data game yang sudah bersih, dengan limit.
    """
    if df_clean.empty:
        return {"error": "Data tidak tersedia."}
    
    # --- PERBAIKAN DI SINI ---
    # .to_json() akan mengubah NaN -> null, lalu json.loads() mengubahnya jadi dict
    result_json = df_clean.head(limit).to_json(orient="records")
    result = json.loads(result_json)
    return {"count": len(result), "data": result}

@app.get("/games/top")
def get_top_games(n: int = Query(10, title="Top N", description="Jumlah game teratas yang ingin ditampilkan", ge=1, le=100)):
    """
    Mendapatkan Top N game berdasarkan 'total_sales'.
    """
    if df_clean.empty:
        return {"error": "Data tidak tersedia."}
    
    top_n = df_clean.nlargest(n, 'total_sales')
    
    # --- PERBAIKAN DI SINI ---
    result_json = top_n.to_json(orient="records")
    result = json.loads(result_json)
    return {"count": len(result), "data": result}

@app.get("/games/search")
def search_games(query: str = Query(..., title="Search Query", description="Teks untuk dicari di judul game", min_length=3)):
    """
    Mencari game yang judulnya mengandung teks 'query'.
    """
    if df_clean.empty:
        return {"error": "Data tidak tersedia."}
    
    search_result = df_clean[df_clean['title'].str.contains(query, case=False, na=False)]
    
    if search_result.empty:
        return {"message": f"Tidak ada game yang ditemukan dengan query: '{query}'"}
        
    # --- PERBAIKAN DI SINI ---
    result_json = search_result.to_json(orient="records")
    result = json.loads(result_json)
    return {"count": len(result), "data": result}