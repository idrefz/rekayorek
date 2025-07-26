import streamlit as st
import pandas as pd
from geopy.distance import geodesic
from io import BytesIO
import time

st.set_page_config(page_title="Rekomendasi ODP Cepat", layout="wide")

def calculate_distance_and_flag(row, odp_df, lat_col, lon_col, sto_col=None):
    """Menghitung jarak terdekat dengan optimasi berdasarkan STO"""
    pelanggan_coord = (row[lat_col], row[lon_col])
    
    min_distance = float('inf')
    best_odp = None
    has_odp_in_range = False
    
    # Filter ODP berdasarkan STO pelanggan jika kolom STO tersedia
    if sto_col is not None and 'STO' in odp_df.columns:
        filtered_odp = odp_df[odp_df['STO'] == row[sto_col]]
    else:
        filtered_odp = odp_df
    
    for _, odp_row in filtered_odp.iterrows():
        odp_coord = (odp_row['LATITUDE'], odp_row['LONGITUDE'])
        distance = geodesic(pelanggan_coord, odp_coord).meters
        
        # Cek ODP dalam radius 200m
        if distance <= 200:
            has_odp_in_range = True
            if distance < min_distance:
                min_distance = distance
                best_odp = odp_row
    
    # Buat hasil
    result = {
        'ODP_TERDEKAT': best_odp['ODP_NAME'] if best_odp is not None else None,
        'JARAK_METER': round(min_distance, 2) if best_odp is not None else None,
        'ODP_AVAI': best_odp['AVAI'] if best_odp is not None else None,
        'ODP_USED': best_odp['USED'] if best_odp is not None else None,
        'ODP_STO': best_odp['STO'] if best_odp is not None and 'STO' in best_odp else None,
        'STATUS_REKOMENDASI': None,
        'KETERANGAN': None
    }
    
    # Tentukan status rekomendasi
    if best_odp is not None:
        result['STATUS_REKOMENDASI'] = 'ODP Tersedia'
        result['KETERANGAN'] = f"ODP {best_odp['ODP_NAME']} (Avail: {best_odp['AVAI']})"
    elif has_odp_in_range:
        result['STATUS_REKOMENDASI'] = 'Potensi PT2/PT3'
        result['KETERANGAN'] = "Ada ODP dalam radius 200m tetapi tidak memenuhi kriteria"
    else:
        result['STATUS_REKOMENDASI'] = 'Tidak Ada ODP'
        result['KETERANGAN'] = "Tidak ada ODP dalam radius 200m"
    
    return pd.Series(result)

def main():
    st.title("🚀 Rekomendasi ODP Cepat dengan Filter")
    
    # Upload data ODP
    with st.expander("1. Upload dan Filter Data ODP", expanded=True):
        odp_file = st.file_uploader("Pilih file Excel/CSV data ODP", 
                                  type=['xlsx', 'xls', 'csv'], 
                                  key="odp_uploader")
        
        odp_df = None
        if odp_file is not None:
            try:
                if odp_file.name.endswith('.csv'):
                    odp_df = pd.read_csv(odp_file)
                else:
                    odp_df = pd.read_excel(odp_file)
                
                # Validasi kolom penting
                required_cols = ['ODP_NAME', 'LATITUDE', 'LONGITUDE', 'AVAI', 'USED']
                missing_cols = [col for col in required_cols if col not in odp_df.columns]
                
                if missing_cols:
                    st.error(f"Kolom penting tidak ditemukan: {', '.join(missing_cols)}")
                else:
                    st.success(f"Data ODP berhasil dibaca! {len(odp_df)} ODP ditemukan.")
                    
                    # Filter ODP berdasarkan Avail
                    min_avail = st.slider("Filter ODP dengan Avail minimal:", 
                                         min_value=0, 
                                         max_value=16,
                                         value=6,  # Default value
                                         help="Atur nilai minimal Avail untuk ODP yang akan dipertimbangkan")
                    
                    filtered_odp = odp_df[odp_df['AVAI'] >= min_avail]
                    st.info(f"ODP yang memenuhi kriteria (Avail ≥ {min_avail}): {len(filtered_odp)} dari {len(odp_df)}")
                    
                    # Tampilkan preview
                    if st.checkbox("Tampilkan preview data ODP"):
                        st.dataframe(filtered_odp.head())
            except Exception as e:
                st.error(f"Error membaca data ODP: {str(e)}")
    
    # Upload data pelanggan
    with st.expander("2. Upload Data Pelanggan", expanded=True):
        pelanggan_file = st.file_uploader("Pilih file Excel/CSV data pelanggan", 
                                        type=['xlsx', 'xls', 'csv'], 
                                        key="pelanggan_uploader")
        
        pelanggan_df = None
        if pelanggan_file is not None and odp_df is not None:
            try:
                if pelanggan_file.name.endswith('.csv'):
                    pelanggan_df = pd.read_csv(pelanggan_file)
                else:
                    pelanggan_df = pd.read_excel(pelanggan_file)
                
                st.success(f"Data pelanggan berhasil dibaca! {len(pelanggan_df)} pelanggan ditemukan.")
                
                # Pilih kolom
                cols = pelanggan_df.columns.tolist()
                
                col1, col2 = st.columns(2)
                with col1:
                    lat_col = st.selectbox("Pilih kolom Latitude", cols, 
                                         index=cols.index('latitude') if 'latitude' in cols else 0)
                with col2:
                    lon_col = st.selectbox("Pilih kolom Longitude", cols, 
                                         index=cols.index('longitude') if 'longitude' in cols else 1 if len(cols) > 1 else 0)
                
                # Pilih kolom STO jika ada
                sto_col = None
                if 'STO' in cols:
                    use_sto = st.checkbox("Gunakan data STO untuk optimasi pencarian", value=True)
                    if use_sto:
                        sto_col = 'STO'
                        st.info("Pencarian akan dioptimasi berdasarkan STO pelanggan")
                
                # Validasi data koordinat
                pelanggan_df[lat_col] = pd.to_numeric(pelanggan_df[lat_col], errors='coerce')
                pelanggan_df[lon_col] = pd.to_numeric(pelanggan_df[lon_col], errors='coerce')
                pelanggan_df = pelanggan_df.dropna(subset=[lat_col, lon_col])
                
                if st.checkbox("Tampilkan preview data pelanggan"):
                    st.dataframe(pelanggan_df.head())
            except Exception as e:
                st.error(f"Error membaca data pelanggan: {str(e)}")
    
    # Proses rekomendasi
    if odp_df is not None and pelanggan_df is not None:
        st.subheader("3. Proses Rekomendasi")
        
        if st.button("🚀 Mulai Proses Rekomendasi", type="primary"):
            with st.spinner('Memproses data...'):
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Hitung ODP terdekat untuk setiap pelanggan
                results = []
                total_pelanggan = len(pelanggan_df)
                
                for i, (_, row) in enumerate(pelanggan_df.iterrows()):
                    # Update progress
                    progress = (i + 1) / total_pelanggan
                    progress_bar.progress(progress)
                    status_text.text(f"Memproses {i+1} dari {total_pelanggan} pelanggan...")
                    
                    # Hitung rekomendasi
                    result = calculate_distance_and_flag(row, filtered_odp, lat_col, lon_col, sto_col)
                    results.append(result)
                
                # Gabungkan hasil
                final_df = pd.concat([pelanggan_df, pd.DataFrame(results)], axis=1)
                
                # Hitung statistik
                stat_df = pd.DataFrame({
                    'Kategori': ['ODP Tersedia', 'Potensi PT2/PT3', 'Tidak Ada ODP'],
                    'Jumlah': [
                        len(final_df[final_df['STATUS_REKOMENDASI'] == 'ODP Tersedia']),
                        len(final_df[final_df['STATUS_REKOMENDASI'] == 'Potensi PT2/PT3']),
                        len(final_df[final_df['STATUS_REKOMENDASI'] == 'Tidak Ada ODP'])
                    ],
                    'Persentase': [
                        f"{(len(final_df[final_df['STATUS_REKOMENDASI'] == 'ODP Tersedia']) / total_pelanggan * 100:.1f}%",
                        f"{(len(final_df[final_df['STATUS_REKOMENDASI'] == 'Potensi PT2/PT3']) / total_pelanggan * 100:.1f}%",
                        f"{(len(final_df[final_df['STATUS_REKOMENDASI'] == 'Tidak Ada ODP']) / total_pelanggan * 100:.1f}%"
                    ]
                })
                
                progress_bar.empty()
                status_text.empty()
                
                st.success("✅ Proses selesai!")
                
                # Tampilkan statistik
                st.subheader("📊 Statistik Rekomendasi")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("ODP Tersedia", 
                            stat_df[stat_df['Kategori'] == 'ODP Tersedia']['Jumlah'].values[0],
                            stat_df[stat_df['Kategori'] == 'ODP Tersedia']['Persentase'].values[0])
                with col2:
                    st.metric("Potensi PT2/PT3", 
                            stat_df[stat_df['Kategori'] == 'Potensi PT2/PT3']['Jumlah'].values[0],
                            stat_df[stat_df['Kategori'] == 'Potensi PT2/PT3']['Persentase'].values[0])
                with col3:
                    st.metric("Tidak Ada ODP", 
                            stat_df[stat_df['Kategori'] == 'Tidak Ada ODP']['Jumlah'].values[0],
                            stat_df[stat_df['Kategori'] == 'Tidak Ada ODP']['Persentase'].values[0])
                
                # Tampilkan hasil
                st.subheader("📋 Detail Rekomendasi")
                st.dataframe(final_df)
                
                # Download hasil
                st.subheader("💾 Download Hasil")
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    final_df.to_excel(writer, index=False, sheet_name='Rekomendasi')
                    stat_df.to_excel(writer, index=False, sheet_name='Statistik')
                    filtered_odp.to_excel(writer, index=False, sheet_name='ODP_Filtered')
                
                st.download_button(
                    label="Unduh Hasil Lengkap (Excel)",
                    data=output.getvalue(),
                    file_name='rekomendasi_odp_cepat.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    help="File Excel berisi 3 sheet: Rekomendasi, Statistik, dan Data ODP Filter"
                )

if __name__ == "__main__":
    main()
