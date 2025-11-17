import pandas as pd
import numpy as np
from fastapi import FastAPI, Query, HTTPException
import json
from typing import Optional, List, Literal

# --- 1. DUPLIKASI LOGIKA PEMBERSIHAN DATA ---
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
    
    df_clean = df.dropna(subset=['total_sales']).copy()
    df_clean['release_date'] = pd.to_datetime(df_clean['release_date'], errors='coerce')
    df_clean['release_year'] = df_clean['release_date'].dt.year
    df_clean['release_year'] = df_clean['release_year'].fillna(0).astype(int)
    regional_cols = ['na_sales', 'jp_sales', 'pal_sales', 'other_sales']
    df_clean[regional_cols] = df_clean[regional_cols].fillna(0)
    df_clean['genre'] = df_clean['genre'].fillna('Unknown')
    df_clean['console'] = df_clean['console'].fillna('Unknown')
    df_clean['critic_score'] = df_clean['critic_score'].replace(0.0, np.nan)
    
    return df_clean

# --- FUNGSI HELPER: Konversi DataFrame ke JSON dengan aman ---
def safe_df_to_response(df):
    """
    Mengonversi DataFrame ke JSON, menangani NaN/NaT dengan benar.
    """
    result_json = df.to_json(orient="records")
    return json.loads(result_json)

# --- 2. Inisialisasi Aplikasi FastAPI ---
app = FastAPI(
    title="Game Sales API (Simple URL)",
    description="API untuk memfilter dan menganalisis data penjualan game.",
    version="1.0.0"
)

# --- 3. Memuat Data Saat Startup ---
print("Memuat dan membersihkan data untuk API...")
try:
    df_clean = get_clean_data_for_api("vgchartz-2024.csv")
    if df_clean is None:
        raise RuntimeError("Gagal memuat file CSV. Pastikan 'vgchartz-2024.csv' ada.")
    unique_genres = sorted(df_clean['genre'].unique().tolist())
    unique_consoles = sorted(df_clean['console'].unique().tolist())
    print("Data berhasil dimuat dan dibersihkan untuk API.")
except Exception as e:
    print(f"FATAL ERROR saat startup: {e}")
    df_clean = pd.DataFrame() 
    unique_genres = []
    unique_consoles = []

# --- 4. Mendefinisikan Endpoint (URL Sederhana) ---

@app.get("/")
def read_root():
    return {
        "message": "Selamat datang di Game Sales API!",
        "documentation": "/docs"
    }

# --- PERUBAHAN: Endpoint Metadata ---
@app.get("/genres")
def get_genres():
    """
    Mendapatkan daftar unik semua Genre dalam data.
    """
    return {"genres": unique_genres}

@app.get("/consoles")
def get_consoles():
    """
    Mendapatkan daftar unik semua Konsol dalam data.
    """
    return {"consoles": unique_consoles}

# --- PERUBAHAN: Endpoint Stats/KPI ---
@app.get("/stats")
def get_global_stats():
    """
    Mendapatkan statistik/KPI global dari seluruh dataset yang bersih.
    """
    if df_clean.empty:
        raise HTTPException(status_code=503, detail="Data tidak tersedia.")
    stats = {
        "total_games_in_dataset": len(df_clean),
        "total_global_sales_miliar": (df_clean['total_sales'].sum() / 1000),
        "average_critic_score": df_clean['critic_score'].mean(),
    }
    return stats

# --- PERUBAHAN: Endpoint Filter Utama ---
@app.get("/games")
def get_filtered_games(
    genres: Optional[List[str]] = Query(None, description="Filter berdasarkan satu atau lebih genre."),
    consoles: Optional[List[str]] = Query(None, description="Filter berdasarkan satu atau lebih konsol."),
    min_year: Optional[int] = Query(None, description="Tahun rilis minimum.", ge=1970),
    max_year: Optional[int] = Query(None, description="Tahun rilis maksimum.", le=2025),
    min_score: Optional[float] = Query(None, description="Skor kritikus minimum (0.0-10.0).", ge=0.0, le=10.0),
    max_score: Optional[float] = Query(None, description="Skor kritikus maksimum (0.0-10.0).", ge=0.0, le=10.0),
    search_query: Optional[str] = Query(None, description="Cari teks di dalam judul game.", min_length=3),
    sort_by: Optional[str] = Query("total_sales", description="Kolom untuk mengurutkan (misal: 'total_sales', 'critic_score', 'release_year')"),
    ascending: bool = Query(False, description="Urutkan secara ascending (True) atau descending (False)"),
    skip: int = Query(0, description="Jumlah data untuk dilewati (pagination).", ge=0),
    limit: int = Query(100, description="Jumlah data maksimum untuk ditampilkan (pagination).", ge=1, le=1000)
):
    """
    Endpoint utama untuk mendapatkan data game dengan filter canggih.
    """
    if df_clean.empty:
        raise HTTPException(status_code=503, detail="Data tidak tersedia.")

    temp_df = df_clean.copy()
    
    # Terapkan Filter
    if genres:
        temp_df = temp_df[temp_df['genre'].isin(genres)]
    if consoles:
        temp_df = temp_df[temp_df['console'].isin(consoles)]
    if search_query:
        temp_df = temp_df[temp_df['title'].str.contains(search_query, case=False, na=False)]
    if min_year:
        temp_df = temp_df[temp_df['release_year'] >= min_year]
    if max_year:
        temp_df = temp_df[temp_df['release_year'] <= max_year]
    if min_score:
        temp_df = temp_df[temp_df['critic_score'] >= min_score]
    if max_score:
        temp_df = temp_df[temp_df['critic_score'] <= max_score]
        
    if temp_df.empty:
        return {"message": "Tidak ada data yang cocok dengan filter Anda."}

    # Terapkan Pengurutan
    if sort_by in temp_df.columns:
        temp_df = temp_df.sort_values(by=sort_by, ascending=ascending)
    else:
        temp_df = temp_df.sort_values(by="total_sales", ascending=False)
        
    total_matches = len(temp_df)
    paginated_df = temp_df.iloc[skip : skip + limit]
    
    result = safe_df_to_response(paginated_df)
    
    return {
        "total_matches_before_pagination": total_matches,
        "showing_results": len(result),
        "skip": skip,
        "limit": limit,
        "data": result
    }

# --- PERUBAHAN: Endpoint Agregasi ---
@app.get("/summary")
def get_summary_by_group(
    # --- Parameter Agregasi ---
    group_by: Literal["genre", "console", "release_year", "publisher"] = Query(
        "genre", 
        description="Kolom yang ingin Anda gunakan untuk 'group by' (mengelompokkan)."
    ),
    
    # --- Parameter Filter (Opsional, salin dari atas) ---
    genres: Optional[List[str]] = Query(None, description="Filter berdasarkan satu atau lebih genre."),
    consoles: Optional[List[str]] = Query(None, description="Filter berdasarkan satu atau lebih konsol."),
    min_year: Optional[int] = Query(None, description="Tahun rilis minimum.", ge=1970),
    max_year: Optional[int] = Query(None, description="Tahun rilis maksimum.", le=2025),
    min_score: Optional[float] = Query(None, description="Skor kritikus minimum (0.0-10.0).", ge=0.0, le=10.0),
    max_score: Optional[float] = Query(None, description="Skor kritikus maksimum (0.0-10.0).", ge=0.0, le=10.0),
    search_query: Optional[str] = Query(None, description="Cari teks di dalam judul game.", min_length=3)
):
    """
    Endpoint canggih untuk mendapatkan data agregat (ringkasan) 
    yang sudah di-groupby dan di-sum. Sangat cepat untuk membuat grafik.
    """
    if df_clean.empty:
        raise HTTPException(status_code=503, detail="Data tidak tersedia.")

    # 1. Mulai dengan salinan data bersih
    temp_df = df_clean.copy()
    
    # 2. Terapkan Filter
    if genres:
        temp_df = temp_df[temp_df['genre'].isin(genres)]
    if consoles:
        temp_df = temp_df[temp_df['console'].isin(consoles)]
    if search_query:
        temp_df = temp_df[temp_df['title'].str.contains(search_query, case=False, na=False)]
    if min_year:
        temp_df = temp_df[temp_df['release_year'] >= min_year]
    if max_year:
        temp_df = temp_df[temp_df['release_year'] <= max_year]
    if min_score:
        temp_df = temp_df[temp_df['critic_score'] >= min_score]
    if max_score:
        temp_df = temp_df[temp_df['critic_score'] <= max_score]
        
    if temp_df.empty:
        return {"message": "Tidak ada data yang cocok dengan filter Anda."}

    # 3. --- INTI AGREGRASI ---
    if group_by == 'release_year':
        temp_df = temp_df[temp_df['release_year'] > 1970]

    try:
        summary_df = temp_df.groupby(group_by).agg(
            total_sales=('total_sales', 'sum'),
            na_sales=('na_sales', 'sum'),
            jp_sales=('jp_sales', 'sum'),
            pal_sales=('pal_sales', 'sum'),
            other_sales=('other_sales', 'sum'),
            game_count=('title', 'size') 
        ).reset_index()
        
        summary_df = summary_df.sort_values(by="total_sales", ascending=False)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Gagal melakukan group-by pada '{group_by}'. Error: {e}")

    # 4. Konversi ke JSON dan kembalikan
    result = safe_df_to_response(summary_df)
    
    return {
        "group_by_column": group_by,
        "total_groups": len(result),
        "data": result
    }