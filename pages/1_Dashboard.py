import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import google.generativeai as genai

# --- 1. Konfigurasi Halaman ---
st.set_page_config(page_title="Dashboard Interaktif",
                   page_icon="📊",
                   layout="wide")

@st.cache_data
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Gagal memuat data: File '{file_path}' tidak ditemukan. Pastikan file ada di folder utama.")
        return None
    
    df_cleaned = df.dropna(subset=['total_sales']).copy()
    df_cleaned['release_date'] = pd.to_datetime(df_cleaned['release_date'])
    df_cleaned['release_year'] = df_cleaned['release_date'].dt.year
    regional_cols = ['na_sales', 'jp_sales', 'pal_sales', 'other_sales']
    df_cleaned[regional_cols] = df_cleaned[regional_cols].fillna(0)
    df_cleaned['genre'] = df_cleaned['genre'].fillna('Unknown')
    df_cleaned['console'] = df_cleaned['console'].fillna('Unknown')
    df_cleaned['release_year'] = df_cleaned['release_year'].fillna(0)
    df_cleaned['critic_score'] = df_cleaned['critic_score'].replace(0.0, np.nan)
    
    return df_cleaned

df = load_data('vgchartz-2024.csv')

if df is None:
    st.stop() 

st.sidebar.header("Filters Dashboard 📊")

# --- Logika Filter Bertingkat Dimulai ---

# 1. Gambar filter KONSOL terlebih dahulu (Filter Induk)
all_consoles = df['console'].unique()
selected_consoles = st.sidebar.multiselect("Pilih Konsol:", options=all_consoles, default=[])

# 2. Tentukan data yang akan digunakan untuk membuat filter Genre
#    Berdasarkan pilihan di filter Konsol.
if selected_consoles:
    # Jika pengguna MEMILIH konsol, filter DataFrame HANYA untuk konsol tsb
    df_for_genre_options = df[df['console'].isin(selected_consoles)]
else:
    # Jika pengguna TIDAK memilih konsol, gunakan seluruh DataFrame
    df_for_genre_options = df

# 3. Dapatkan daftar genre yang tersedia DARI data yang sudah difilter tadi
available_genres = df_for_genre_options['genre'].unique()

# 4. Gambar filter GENRE (Filter Anak)
#    Gunakan 'available_genres' sebagai options, BUKAN 'all_genres'
selected_genres = st.sidebar.multiselect(
    "Pilih Genre (berdasarkan konsol):", 
    options=available_genres, 
    default=[]
)

# --- Logika Filter Bertingkat Selesai ---


# 5. Filter Tahun (Independen)
min_year = int(df.loc[df['release_year'] > 0, 'release_year'].min())
max_year = int(df['release_year'].max())
selected_year_range = st.sidebar.slider(
    "Pilih Rentang Tahun Rilis:",
    min_value=min_year, max_value=max_year, value=(min_year, max_year) 
)

# ... (setelah st.sidebar.slider untuk tahun) ...
# --- 4. Layout: Sidebar (Filter) ---
# ... (filter genre, konsol, tahun) ...

# 6. Filter Skor Kritikus (KUALITAS)
selected_score_range = st.sidebar.slider(
    "Filter berdasarkan Skor Kritikus (0-10):",
    min_value=0.0,
    max_value=10.0,
    value=(0.0, 10.0), 
    step=0.5
)

# --- TAMBAHAN BARU: Checkbox untuk data tanpa skor ---
include_no_score = st.sidebar.checkbox(
    "Sertakan game tanpa skor (Kosong)", 
    value=True # Defaultnya, kita sertakan
)

# --- 5. Terapkan Filter ---
df_filtered = df.copy()

# Terapkan filter KATEGORI
if selected_genres:
    df_filtered = df_filtered[df_filtered['genre'].isin(selected_genres)]
if selected_consoles:
    df_filtered = df_filtered[df_filtered['console'].isin(selected_consoles)]

# Terapkan filter TAHUN
df_filtered = df_filtered[
    (df_filtered['release_year'] >= selected_year_range[0]) &
    (df_filtered['release_year'] <= selected_year_range[1])
]

# Terapkan filter KATEGORI
if selected_genres:
    df_filtered = df_filtered[df_filtered['genre'].isin(selected_genres)]
if selected_consoles:
    df_filtered = df_filtered[df_filtered['console'].isin(selected_consoles)]

# Terapkan filter TAHUN
df_filtered = df_filtered[
    (df_filtered['release_year'] >= selected_year_range[0]) &
    (df_filtered['release_year'] <= selected_year_range[1])
]

# 1. Definisikan "Punya Skor" sebagai game yang skornya masuk dalam rentang slider
condition_score_in_range = (
    df_filtered['critic_score'].between(selected_score_range[0], selected_score_range[1])
)

# 2. Definisikan "Tidak Punya Skor"
condition_no_score = (
    df_filtered['critic_score'].isna()
)

# 3. Terapkan filter berdasarkan pilihan Checkbox
if include_no_score:
    # JIKA dicentang: Tampilkan game (Dalam Rentang) ATAU (Tanpa Skor)
    df_filtered = df_filtered[ condition_score_in_range | condition_no_score ]
else:
    # JIKA TIDAK dicentang: Tampilkan HANYA game (Dalam Rentang)
    df_filtered = df_filtered[ condition_score_in_range ]

# --- 6. Layout: Halaman Utama ---
st.title("📊 Dashboard Interaktif Penjualan Game")
st.markdown("Gunakan filter di sidebar untuk menjelajahi data.")

if df_filtered.empty:
    st.warning("Tidak ada data yang sesuai dengan filter Anda. Coba ubah filter.")
else:
    # --- 7. Metrik Utama ---
    with st.container(border=True):
        st.header("Metrik Utama (Berdasarkan Filter)")
        
        # --- PERBAIKAN 1: Logika Penjualan ---
        total_sales_filtered_miliar = df_filtered['total_sales'].sum() / 1000
        
        total_games_filtered = df_filtered.shape[0]
        avg_critic_score = np.nanmean(df_filtered['critic_score'])

        col1, col2, col3 = st.columns(3)
        
        # --- PERBAIKAN 1 (Label): Ubah "Jt" -> "M" ---
        col1.metric("Total Penjualan (Miliar Unit)", f"{total_sales_filtered_miliar:.2f} M")
        
        col2.metric("Total Game Terfilter", f"{total_games_filtered:,}")
        
        # --- PERBAIKAN 2: Konteks Skor Kritikus ---
        col3.metric("Rerata Skor Kritikus", f"{avg_critic_score:.1f} / 10",
                    help="Skor rata-rata berdasarkan data 'critic_score', dengan rentang 0 (Buruk) hingga 10 (Sempurna).")

        # Ini sudah benar
        top_game_filtered = df_filtered.nlargest(1, 'total_sales').iloc[0]
        st.metric(
            label="Game Terlaris (Sesuai Filter)",
            value=top_game_filtered['title'],
            help=f"Konsol: {top_game_filtered['console']} | Penjualan: {top_game_filtered['total_sales']:.2f} Jt"
        )
        
    # --- 8. Visualisasi Data ---
    with st.container(border=True):
        st.header("Visualisasi Data")
        
        # --- Persiapan Data untuk Visualisasi ---
        top_n_h1 = st.number_input("Tampilkan Top N Game:", min_value=5, max_value=50, value=10, step=5, key="h1_top_n")
        top_n_games_filtered = df_filtered.nlargest(top_n_h1, 'total_sales').copy()
        top_n_games_filtered['unique_title'] = top_n_games_filtered['title'] + " (" + top_n_games_filtered['console'] + ")"
        
        total_na = df_filtered['na_sales'].sum()
        total_jp = df_filtered['jp_sales'].sum()
        total_pal = df_filtered['pal_sales'].sum()
        total_other = df_filtered['other_sales'].sum()
        df_regional = pd.DataFrame({
            'Wilayah': ['Amerika Utara (NA)', 'Jepang (JP)', 'Eropa (PAL)', 'Lainnya (Other)'],
            'Penjualan': [total_na, total_jp, total_pal, total_other]
        })
        
        yearly_sales_filtered = df_filtered[df_filtered['release_year'] > 0].groupby('release_year')['total_sales'].sum().reset_index()
        yearly_sales_filtered['release_year'] = yearly_sales_filtered['release_year'].astype(int)

        # --- Tampilkan Visualisasi ---
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.subheader(f"Top {top_n_h1} Game Terlaris")
            fig_games = px.bar(
                top_n_games_filtered.sort_values('total_sales', ascending=True),
                x=['na_sales', 'jp_sales', 'pal_sales', 'other_sales'], 
                y='unique_title', orientation='h',
                title=f'Top {top_n_h1} Game Terlaris (Breakdown per Wilayah)', 
                labels={'value': 'Total Penjualan (Juta)', 'unique_title': 'Game (Konsol)', 'variable': 'Wilayah'}
            )
            st.plotly_chart(fig_games, use_container_width=True)
            st.success("""
            **Analisis:** Grafik ini menunjukkan game terlaris berdasarkan filter Anda, dipecah per wilayah.
            * **Perhatikan:** Apakah ada game yang sangat dominan di satu wilayah?
            """)

        with col_chart2:
            st.subheader("Proporsi Penjualan per Wilayah")
            fig_regional = px.pie(
                df_regional, names='Wilayah', values='Penjualan',
                title='Proporsi Penjualan per Wilayah (Berdasarkan Filter)', hole=0.2,
            )
            st.plotly_chart(fig_regional, use_container_width=True)
            st.success("""
            **Analisis:** Diagram ini menunjukkan dari mana uang (penjualan) berasal untuk game-game yang Anda filter.
            * **Coba Filter:** Pilih genre 'Role-Playing' atau konsol 'DS'/'3DS'. Anda akan lihat porsi Jepang (`jp_sales`) membesar.
            """)

        st.subheader("Tren Penjualan Global per Tahun Rilis")
        fig_trend = px.line(
            yearly_sales_filtered, x='release_year', y='total_sales',
            title='Tren Penjualan Global per Tahun Rilis (Sesuai Filter)',
            labels={'release_year': 'Tahun Rilis', 'total_sales': 'Total Penjualan (Juta)'},
            markers=True
        )
        st.plotly_chart(fig_trend, use_container_width=True)
        st.success("""
        **Analisis:** Grafik ini menunjukkan "masa keemasan" dari game/konsol yang Anda filter.
        * **Puncak Industri:** Jika tidak difilter, Anda akan melihat puncak penjualan game fisik di sekitar 2008-2011 (era Wii, PS3, X360).
        """)


    # Tampilkan data mentah jika dicentang
    if st.checkbox("Tampilkan data mentah (sesuai filter)"):
        st.dataframe(df_filtered)