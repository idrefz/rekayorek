import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import io
from datetime import datetime

# Page configuration
st.set_page_config(layout="wide", page_title="ODP Recommendation System", page_icon="📊")
st.title("📊 ODP Recommendation System")
st.markdown("""
    Sistem ini memberikan rekomendasi ODP terbaik untuk pelanggan berdasarkan:
    - Jarak terdekat
    - Ketersediaan port
    - Batasan jarak maksimum
""")

# Cache data to improve performance
@st.cache_data
def load_data(uploaded_file):
    if uploaded_file.name.endswith('xlsx'):
        return pd.read_excel(uploaded_file)
    return pd.read_csv(uploaded_file)

def calculate_recommendation(row, odp_df, lat_col, lon_col, sto_column, min_avail, max_distance):
    pelanggan_coord = (row[lat_col], row[lon_col])
    
    # Check for invalid coordinates
    if pd.isnull(pelanggan_coord[0]) or pd.isnull(pelanggan_coord[1]):
        return {
            'Nama ODP Rekomendasi': None,
            'Jarak (meter)': None,
            'AVAI': None,
            'USED': None,
            'IDLE': None,
            'RSV': None,
            'RSK': None,
            'IS_TOTAL': None,
            'Latitude ODP': None,
            'Longitude ODP': None,
            'Status': 'Koordinat pelanggan tidak valid',
            'ODP Terdekat (Jika tidak memenuhi kriteria)': None,
            'Jarak ODP Terdekat (meter)': None
        }

    # Filter by STO if specified
    if sto_column and sto_column in row:
        filtered_odp = odp_df[odp_df['STO'] == row[sto_column]].copy()
    else:
        filtered_odp = odp_df.copy()

    # Calculate distances
    filtered_odp['distance'] = filtered_odp.apply(
        lambda x: geodesic(pelanggan_coord, (x['LATITUDE'], x['LONGITUDE'])).meters, axis=1)
    
    # Find eligible ODPs
    nearby_odp = filtered_odp[filtered_odp['distance'] <= max_distance]
    eligible_odp = nearby_odp[nearby_odp['AVAI'] - nearby_odp['USED'] >= min_avail]

    best_odp = eligible_odp.nsmallest(1, 'distance').squeeze() if not eligible_odp.empty else None
    closest_odp = filtered_odp.nsmallest(1, 'distance').squeeze() if not filtered_odp.empty else None

    # Prepare result
    result = {
        'Nama ODP Rekomendasi': best_odp['ODP_NAME'] if best_odp is not None else None,
        'Jarak (meter)': round(best_odp['distance'], 2) if best_odp is not None else None,
        'AVAI': best_odp['AVAI'] if best_odp is not None else None,
        'USED': best_odp['USED'] if best_odp is not None else None,
        'IDLE': (best_odp['AVAI'] - best_odp['USED']) if best_odp is not None else None,
        'RSV': best_odp.get('RSV') if best_odp is not None else None,
        'RSK': best_odp.get('RSK') if best_odp is not None else None,
        'IS_TOTAL': best_odp.get('IS_TOTAL') if best_odp is not None else None,
        'Latitude ODP': best_odp['LATITUDE'] if best_odp is not None else None,
        'Longitude ODP': best_odp['LONGITUDE'] if best_odp is not None else None,
        'Status': 'Ready PT1' if best_odp is not None else 'Potensi PT2/PT3',
        'ODP Terdekat (Jika tidak memenuhi kriteria)': closest_odp['ODP_NAME'] if best_odp is None and closest_odp is not None else None,
        'Jarak ODP Terdekat (meter)': round(closest_odp['distance'], 2) if best_odp is None and closest_odp is not None else None,
        # Tambahkan latitude dan longitude pelanggan
        'Latitude Pelanggan': row[lat_col],
        'Longitude Pelanggan': row[lon_col]
    }

    return result

# File upload section
st.header("📤 Upload Data")
col1, col2 = st.columns(2)
with col1:
    uploaded_odp = st.file_uploader("Upload File ODP (.xlsx or .csv)", type=["xlsx", "csv"], 
                                  help="File harus mengandung kolom: ODP_NAME, LATITUDE, LONGITUDE, AVAI, USED, STO")
with col2:
    uploaded_pelanggan = st.file_uploader("Upload File Pelanggan (.xlsx or .csv)", type=["xlsx", "csv"],
                                        help="File harus mengandung kolom latitude dan longitude pelanggan")

if uploaded_odp and uploaded_pelanggan:
    try:
        odp_df = load_data(uploaded_odp)
        pelanggan_df = load_data(uploaded_pelanggan)
        
        # Validate ODP dataframe
        required_odp_columns = {'ODP_NAME', 'LATITUDE', 'LONGITUDE', 'AVAI', 'USED'}
        if not required_odp_columns.issubset(odp_df.columns):
            missing = required_odp_columns - set(odp_df.columns)
            st.error(f"File ODP tidak memiliki kolom yang diperlukan: {', '.join(missing)}")
            st.stop()
            
        st.success("Data berhasil dimuat!")

        # Configuration section
        st.header("⚙️ Konfigurasi Parameter")
        
        col1, col2 = st.columns(2)
        with col1:
            lat_col = st.selectbox("Pilih kolom Latitude pelanggan", pelanggan_df.columns,
                                  help="Kolom yang berisi latitude pelanggan")
            lon_col = st.selectbox("Pilih kolom Longitude pelanggan", pelanggan_df.columns,
                                  help="Kolom yang berisi longitude pelanggan")
            nama_kolom = st.selectbox("Pilih kolom Nama pelanggan", pelanggan_df.columns,
                                    help="Kolom yang berisi nama/identifikasi pelanggan")
        with col2:
            sto_col = st.selectbox("Pilih kolom STO pelanggan (opsional)", ['-'] + list(pelanggan_df.columns),
                                 help="Kolom yang berisi STO pelanggan untuk filter tambahan")
            min_avail = st.slider("Minimum Port Tersedia (AVAI - USED)", 0, 8, 2,
                                help="Jumlah port minimal yang harus tersedia di ODP")
            max_distance = st.slider("Jarak maksimum (meter)", 100, 1000, 300, step=50,
                                   help="Jarak maksimum dari pelanggan ke ODP")

        if st.button("🚀 Proses Rekomendasi", type="primary"):
            with st.spinner("Memproses data pelanggan..."):
                results_list = []
                progress_bar = st.progress(0)
                progress_text = st.empty()
                total = len(pelanggan_df)

                for i, (_, row) in enumerate(pelanggan_df.iterrows()):
                    result = calculate_recommendation(
                        row, odp_df, lat_col, lon_col,
                        sto_col if sto_col != '-' else None,
                        min_avail, max_distance
                    )
                    results_list.append(result)
                    percent_complete = (i + 1) / total
                    progress_bar.progress(percent_complete)
                    progress_text.text(f"Progres: {i+1}/{total} pelanggan diproses ({percent_complete*100:.1f}%)")

                results = pd.DataFrame(results_list)

            # Combine results with customer data
            if sto_col != '-':
                base_df = pelanggan_df[[nama_kolom, sto_col, lat_col, lon_col]]  # Tambahkan lat/lon pelanggan
            else:
                base_df = pelanggan_df[[nama_kolom, lat_col, lon_col]]  # Tambahkan lat/lon pelanggan

            final_df = pd.concat([base_df.reset_index(drop=True), results.reset_index(drop=True)], axis=1)

            # Display results
            st.header("📋 Hasil Rekomendasi")
            st.dataframe(final_df, use_container_width=True)

            # Add summary statistics
            st.subheader("📊 Statistik Rekomendasi")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pelanggan", len(final_df))
            with col2:
                ready = final_df[final_df['Status'] == 'Ready PT1'].shape[0]
                st.metric("Ready PT1", f"{ready} ({ready/len(final_df)*100:.1f}%)")
            with col3:
                potensi = final_df[final_df['Status'] == 'Potensi PT2/PT3'].shape[0]
                st.metric("Potensi PT2/PT3", f"{potensi} ({potensi/len(final_df)*100:.1f}%)")

            # Download button
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            towrite = io.BytesIO()
            final_df.to_excel(towrite, index=False, sheet_name='Rekomendasi')
            towrite.seek(0)

            st.download_button(
                label="📥 Download Hasil Rekomendasi",
                data=towrite,
                file_name=f"hasil_rekomendasi_odp_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="File Excel akan berisi rekomendasi ODP beserta koordinat pelanggan"
            )

    except Exception as e:
        st.error(f"Terjadi kesalahan: {str(e)}")
        st.stop()
else:
    st.info("Silakan upload file ODP dan file Pelanggan untuk memulai proses rekomendasi.")
