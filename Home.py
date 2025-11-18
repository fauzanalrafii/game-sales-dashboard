import streamlit as st

st.set_page_config(page_title="Home", page_icon="🏠", layout="centered")

st.title("Selamat Datang di Dashboard Analisis Penjualan Game 🎮")

# st.image("link_ke_gambar_game_keren.jpg") # Opsional, jika punya gambar

st.markdown("""
Selamat datang di aplikasi analisis data penjualan video game. Data ini diambil dari `vgchartz-2024.csv` dan mencakup puluhan ribu game.

Aplikasi ini memiliki dua halaman utama:

1.  **Dashboard Interaktif:**
    Halaman untuk eksplorasi data secara bebas. Anda dapat menggunakan filter di sidebar untuk memotong data berdasarkan Genre, Konsol, dan Tahun Rilis.

2.  **Analisis Spesifik:**
    Halaman yang menjawab 4 pertanyaan bisnis kunci secara mendalam, lengkap dengan visualisasi dan kontrol interaktif.

**Silakan pilih halaman yang Anda ingginkan dari menu navigasi di sebelah kiri.**
""")