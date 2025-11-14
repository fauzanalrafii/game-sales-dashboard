import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import google.generativeai as genai

st.set_page_config(page_title="Analisis Spesifik", page_icon="💡", layout="wide")

@st.cache_data
def load_and_clean_data(file_path):
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"Error: File '{file_path}' tidak ditemukan. Pastikan file ada di folder utama.")
        return None
    df_clean = df.dropna(subset=['total_sales']).copy()
    df_clean['release_date'] = pd.to_datetime(df_clean['release_date'])
    df_clean['release_year'] = df_clean['release_date'].dt.year
    df_clean['release_year'] = df_clean['release_year'].fillna(0).astype(int)
    regional_cols = ['na_sales', 'jp_sales', 'pal_sales', 'other_sales']
    df_clean[regional_cols] = df_clean[regional_cols].fillna(0)
    df_clean['genre'] = df_clean['genre'].fillna('Unknown')
    df_clean['console'] = df_clean['console'].fillna('Unknown')
    df_clean['critic_score'] = df_clean['critic_score'].replace(0.0, np.nan)
    return df_clean

# --- 4. Layout Halaman Utama ---
st.title("💡 Analisis Spesifik & Interaktif")
st.markdown("Halaman ini menjawab 4 pertanyaan kunci dengan kontrol interaktif di setiap tab.")

df = load_and_clean_data('vgchartz-2024.csv')

if df is not None:
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "Q1: Judul Terlaris", 
        "Q2: Tren Industri", 
        "Q3: Spesialisasi Konsol",
        "Q4: Skor Kritikus vs. Penjualan"
    ])

    # --- Isi Tab 1: Q1 (Judul Terlaris) ---
    with tab1:
        st.header("Q1: Judul apa yang paling banyak terjual di seluruh dunia?")
        top_n = st.number_input("Tampilkan Top N Game:", min_value=5, max_value=50, value=10, step=5, key="q1_top_n")
        
        top_games = df.nlargest(top_n, 'total_sales').copy()
        top_games['unique_title'] = top_games['title'] + " (" + top_games['console'] + ")"
        
        fig_q1 = px.bar(
            top_games.sort_values('total_sales', ascending=True),
            x=['na_sales', 'jp_sales', 'pal_sales', 'other_sales'], 
            y='unique_title', orientation='h',
            title=f'Top {top_n} Game Terlaris (Breakdown per Wilayah)', 
            labels={'value': 'Total Penjualan (Juta)', 'unique_title': 'Game (Konsol)', 'variable': 'Wilayah'}
        )
        st.plotly_chart(fig_q1, use_container_width=True)
        
        st.success(f"**Kesimpulan:** Daftar Top {top_n} ini didominasi oleh franchise ikonik seperti GTA dan CoD. Untuk mendapatkan insight lebih mendalam, silakan gunakan tombol AI di bawah.")

    # --- Isi Tab 2: Q2 (Tren Industri) ---
    with tab2:
        st.header("Q2: Tahun mana yang penjualannya tertinggi? Apakah industri bertumbuh?")
        
        yearly_sales = df[df['release_year'] > 1970].groupby('release_year')['total_sales'].sum().reset_index()
        
        if not yearly_sales.empty:
            highest_year_data = yearly_sales.loc[yearly_sales['total_sales'].idxmax()]
            st.metric(label="Tahun Penjualan Puncak (Game Fisik)", value=f"{int(highest_year_data['release_year'])}", delta=f"{highest_year_data['total_sales']:.2f} Juta Unit")
        
        fig_q2 = px.line(
            yearly_sales, x='release_year', y='total_sales',
            title='Tren Penjualan Global per Tahun Rilis',
            labels={'release_year': 'Tahun Rilis', 'total_sales': 'Total Penjualan (Juta)'}, markers=True
        )
        fig_q2.update_layout(xaxis_rangeslider_visible=True)
        st.plotly_chart(fig_q2, use_container_width=True)
        
        st.success("**Kesimpulan:** Puncak penjualan game fisik terjadi di era 2008-2011.")
        
        st.markdown("---")

    # --- Isi Tab 3: Q3 (Spesialisasi Konsol) ---
    with tab3:
        st.header("Q3: Apakah ada konsol yang berspesialisasi pada genre tertentu?")
        
        all_consoles = df.groupby('console')['total_sales'].sum().sort_values(ascending=False).index.tolist()
        default_top_5 = all_consoles[:5]
        selected_consoles = st.multiselect("Pilih Konsol untuk Dibandingkan:", options=all_consoles, default=default_top_5)
        
        if selected_consoles:
            df_top_consoles = df[df['console'].isin(selected_consoles)]
            console_genre_sales = df_top_consoles.groupby(['console', 'genre'])['total_sales'].sum()
            console_total_sales = df_top_consoles.groupby('console')['total_sales'].sum()
            console_genre_percent = console_genre_sales.div(console_total_sales, level='console') * 100
            df_plot_q3 = console_genre_percent.reset_index(name='percent_of_console_sales')

            fig_q3 = px.bar(
                df_plot_q3, x='console', y='percent_of_console_sales', color='genre',
                barmode='stack', title='Proporsi Genre (Spesialisasi) untuk Konsol Terpilih',
                labels={'percent_of_console_sales': 'Persentase Penjualan Genre (%)', 'console': 'Konsol', 'genre': 'Genre'},
                height=600
            )
            st.plotly_chart(fig_q3, use_container_width=True)

            st.success("**Kesimpulan:** Beberapa konsol menunjukkan spesialisasi genre yang jelas, misalnya Nintendo dengan simulasi dan RPG, sementara PlayStation memiliki portofolio genre yang lebih beragam.")
            
            st.markdown("---")
        else:
            st.warning("Silakan pilih minimal satu konsol.")

    # --- Isi Tab 5: Q4 (Skor Kritikus vs. Penjualan) ---
    with tab4:
        st.header("Q4: Apakah skor kritikus yang tinggi menjamin penjualan?")
        
        df_scatter = df.dropna(subset=['critic_score', 'total_sales'])
        all_genres_scatter = df_scatter['genre'].unique()
        selected_genre_scatter = st.multiselect(
            "Filter Genre untuk Scatter Plot:",
            options=all_genres_scatter,
            default=['Action', 'Shooter', 'Racing'],
            key="scatter_genre_filter"
        )

        if selected_genre_scatter:
            df_plot_q5 = df_scatter[df_scatter['genre'].isin(selected_genre_scatter)]
            fig_q5 = px.scatter(
                df_plot_q5, x='critic_score', y='total_sales',
                color='genre', hover_data=['title', 'console'],
                title="Hubungan Skor Kritikus vs. Total Penjualan (Global)"
            )
            fig_q5.update_layout(xaxis_title="Skor Kritikus (0-10)", yaxis_title="Total Penjualan (dalam Juta)")
            st.plotly_chart(fig_q5, use_container_width=True)
            
            st.success("**Kesimpulan:** Berdasarkan grafik, Skor kritik tinggi BUKAN jaminan sukses dalam penjualan, tapi skor rendah memiliki kemungkinan gagal yang besar.")
            
            st.markdown("---")
        else:
            st.warning("Pilih minimal satu genre untuk menampilkan scatter plot.")

else:
    st.warning("Gagal memuat data. Silakan cek file 'vgchartz-2024.csv'.")