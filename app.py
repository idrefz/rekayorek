import streamlit as st
import pandas as pd
from geopy.distance import geodesic
from io import BytesIO

st.set_page_config(page_title="Rekomendasi ODP Lengkap", layout="wide")

def calculate_recommendation(row, odp_df, lat_col, lon_col, sto_col=None, min_avail=6, max_distance=200):
    """Menghitung rekomendasi ODP dengan detail lengkap"""
    pelanggan_coord = (row[lat_col], row[lon_col])
    
    best_odp = None
    closest_odp = None
    min_distance = float('inf')
    
    # Filter ODP berdasarkan STO jika tersedia
    if sto_col is not None and 'STO' in odp_df.columns:
        filtered_odp = odp_df[odp_df['STO'] == row[sto_col]]
    else:
        filtered_odp = odp_df
    
    for _, odp_row in filtered_odp.iterrows():
        odp_coord = (odp_row['LATITUDE'], odp_row['LONGITUDE'])
        distance = geodesic(pelanggan_coord, odp_coord).meters
        
        # Simpan ODP terdekat tanpa memandang avail
        if distance < min_distance:
            min_distance = distance
            closest_odp = odp_row
        
        # Prioritaskan ODP yang memenuhi kriteria
        if distance <= max_distance and odp_row['AVAI'] >= min_avail:
            if best_odp is None or distance < min_distance:
                best_odp = odp_row
                min_distance = distance
    
    # Hitung nilai RSV dan RSK jika ada
    rsv = best_odp['RSV'] if best_odp is not None and 'RSV' in best_odp else None
    rsk = best_odp['RSK'] if best_odp is not None and 'RSK' in best_odp else None
    is_total = best_odp['IS_TOTAL'] if best_odp is not None and 'IS_TOTAL' in best_odp else None
    
    # Buat hasil
    result = {
        'Nama ODP Rekomendasi': best_odp['ODP_NAME'] if best_odp is not None else closest_odp['ODP_NAME'] if closest_odp is not None else None,
        'Jarak (meter)': round(min_distance, 2) if best_odp is not None else round(geodesic(pelanggan_coord, (closest_odp['LATITUDE'], closest_odp['LONGITUDE']).meters, 2) if closest_odp is not None else None,
        'AVAI': best_odp['AVAI'] if best_odp is not None else closest_odp['AVAI'] if closest_odp is not None else None,
        'USED': best_odp['USED'] if best_odp is not None else closest_odp['USED'] if closest_odp is not None else None,
        'IDLE': best_odp['AVAI'] - best_odp['USED'] if best_odp is not None and 'AVAI' in best_odp and 'USED' in best_odp else None,
        'RSV': rsv,
        'RSK': rsk,
        'IS_TOTAL': is_total,
        'Status': 'Ready PT1' if best_odp is not None else 'Potensi PT2/PT3',
        'ODP Terdekat (Jika tidak memenuhi kriteria)': closest_odp['ODP_NAME'] if best_odp is None and closest_odp is not None else None,
        'Jarak ODP Terdekat (meter)': round(geodesic(pelanggan_coord, (closest_odp['LATITUDE'], closest_odp['LONGITUDE']).meters, 2) if best_odp is None and closest_odp is not None else None
    }
    
    return pd.Series(result)

def main():
    st.title("📊 Rekomendasi ODP Lengkap")
    
    # Upload data ODP
    with st.expander("1. Upload Data ODP", expanded=True):
        odp_file = st.file_uploader("Pilih file Excel/CSV data ODP", type=['xlsx', 'xls', 'csv'], key="odp_uploader")
        
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
                    
                    # Filter settings
                    min_avail = st.slider("Filter ODP dengan Avail minimal:", 
                                         min_value=0, 
                                         max_value=16,
                                         value=6,
                                         key="min_avail")
                    
                    max_distance = st.slider("Jarak maksimal (meter):",
                                           min_value=50,
                                           max_value=500,
                                           value=200,
                                           key="max_distance")
                    
                    if st.checkbox("Tampilkan preview data ODP"):
                        st.dataframe(odp_df.head())
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
                    nama_kolom = st.selectbox("Pilih kolom Nama Koperasi/Pelanggan", 
                                            cols, 
                                            index=cols.index('Nama Koperasi') if 'Nama Koperasi' in cols else 0)
                with col2:
                    sto_col = st.selectbox("Pilih kolom STO (opsional)", 
                                         ['-'] + cols,
                                         index=0)
                
                col3, col4 = st.columns(2)
                with col3:
                    lat_col = st.selectbox("Pilih kolom Latitude", cols, 
                                         index=cols.index('Latitude') if 'Latitude' in cols else 0)
                with col4:
                    lon_col = st.selectbox("Pilih kolom Longitude", cols, 
                                         index=cols.index('Longitude') if 'Longitude' in cols else 1 if len(cols) > 1 else 0)
                
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
        st.subheader("3. Hasil Rekomendasi")
        
        if st.button("🚀 Mulai Proses Rekomendasi", type="primary"):
            with st.spinner('Memproses data...'):
                try:
                    # Get parameters
                    min_avail = st.session_state.get('min_avail', 6)
                    max_distance = st.session_state.get('max_distance', 200)
                    sto_col = None if sto_col == '-' else sto_col
                    
                    # Hitung rekomendasi
                    results = pelanggan_df.apply(
                        lambda row: calculate_recommendation(
                            row, odp_df, lat_col, lon_col, sto_col, min_avail, max_distance
                        ), 
                        axis=1
                    )
                    
                    # Gabungkan hasil dengan data pelanggan
                    final_df = pd.concat([
                        pelanggan_df[[nama_kolom, sto_col] if sto_col != '-' else pelanggan_df[[nama_kolom]], 
                        results
                    ], axis=1)
                    
                    # Hitung statistik
                    ready_pt1 = final_df[final_df['Status'] == 'Ready PT1']
                    potensi_pt2 = final_df[final_df['Status'] == 'Potensi PT2/PT3']
                    
                    st.success("✅ Proses selesai!")
                    
                    # Tampilkan statistik
                    st.subheader("📊 Statistik Rekomendasi")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Ready PT1", len(ready_pt1))
                    with col2:
                        st.metric("Potensi PT2/PT3", len(potensi_pt2))
                    
                    # Tampilkan hasil
                    st.subheader("📋 Detail Rekomendasi")
                    st.dataframe(final_df)
                    
                    # Download hasil
                    st.subheader("💾 Download Hasil")
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        final_df.to_excel(writer, index=False, sheet_name='Rekomendasi')
                        
                        # Buat sheet statistik
                        stats = pd.DataFrame({
                            'Kategori': ['Ready PT1', 'Potensi PT2/PT3'],
                            'Jumlah': [len(ready_pt1), len(potensi_pt2)],
                            'Persentase': [
                                f"{len(ready_pt1)/len(final_df)*100:.1f}%",
                                f"{len(potensi_pt2)/len(final_df)*100:.1f}%"
                            ]
                        })
                        stats.to_excel(writer, index=False, sheet_name='Statistik')
                    
                    st.download_button(
                        label="Unduh Hasil Lengkap (Excel)",
                        data=output.getvalue(),
                        file_name='rekomendasi_odp_lengkap.xlsx',
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        help="File Excel berisi 2 sheet: Rekomendasi dan Statistik"
                    )
                    
                except Exception as e:
                    st.error(f"Terjadi kesalahan saat memproses: {str(e)}")

if __name__ == "__main__":
    main()
