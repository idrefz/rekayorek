import streamlit as st
import pandas as pd
from geopy.distance import geodesic
from io import BytesIO

st.set_page_config(page_title="Rekomendasi ODP Fleksibel", layout="wide")

def calculate_distance_and_flag(row, odp_df, lat_col, lon_col):
    """Menghitung jarak terdekat dan menentukan flagging"""
    pelanggan_coord = (row[lat_col], row[lon_col])
    
    min_distance = float('inf')
    best_odp = None
    has_odp_in_range = False
    
    for _, odp_row in odp_df.iterrows():
        odp_coord = (odp_row['LATITUDE'], odp_row['LONGITUDE'])
        distance = geodesic(pelanggan_coord, odp_coord).meters
        
        # Cek ODP dalam radius 200m
        if distance <= 200:
            has_odp_in_range = True
            # Prioritaskan ODP dengan avail >= 6
            if odp_row['AVAI'] >= 6 and distance < min_distance:
                min_distance = distance
                best_odp = odp_row
    
    # Buat hasil
    result = {
        'ODP_TERDEKAT': best_odp['ODP_NAME'] if best_odp is not None else None,
        'JARAK_METER': round(min_distance, 2) if best_odp is not None else None,
        'ODP_AVAI': best_odp['AVAI'] if best_odp is not None else None,
        'ODP_USED': best_odp['USED'] if best_odp is not None else None,
        'STATUS_REKOMENDASI': None,
        'KETERANGAN': None
    }
    
    # Tentukan status rekomendasi
    if best_odp is not None:
        result['STATUS_REKOMENDASI'] = 'ODP Tersedia'
        result['KETERANGAN'] = f"ODP {best_odp['ODP_NAME']} dengan avail {best_odp['AVAI']}"
    elif has_odp_in_range:
        result['STATUS_REKOMENDASI'] = 'Potensi PT2/PT3'
        result['KETERANGAN'] = "Ada ODP dalam radius 200m tetapi avail < 6"
    else:
        result['STATUS_REKOMENDASI'] = 'Tidak Ada ODP'
        result['KETERANGAN'] = "Tidak ada ODP dalam radius 200m"
    
    return pd.Series(result)

def detect_coordinate_columns(df, lat_names=['latitude', 'lat'], lon_names=['longitude', 'lon']):
    """Mendeteksi kolom latitude dan longitude secara otomatis"""
    lat_col = None
    lon_col = None
    
    # Cari kolom latitude
    for name in lat_names:
        if name in df.columns:
            lat_col = name
            break
    
    # Cari kolom longitude
    for name in lon_names:
        if name in df.columns:
            lon_col = name
            break
    
    # Jika tidak ditemukan, coba cari berdasarkan pola
    if lat_col is None:
        for col in df.columns:
            if 'lat' in col.lower():
                lat_col = col
                break
    
    if lon_col is None:
        for col in df.columns:
            if 'lon' in col.lower() or 'lng' in col.lower():
                lon_col = col
                break
    
    # Default ke kolom pertama dan kedua jika tidak ditemukan
    if lat_col is None:
        lat_col = df.columns[0]
    if lon_col is None:
        lon_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
    
    return lat_col, lon_col

def main():
    st.title("Rekomendasi ODP - Fleksibel Kolom Koordinat")
    st.write("""
    Aplikasi ini dapat menangani berbagai nama kolom untuk latitude dan longitude pada data pelanggan.
    Sistem akan mencoba mendeteksi kolom koordinat secara otomatis.
    """)
    
    # Upload data ODP
    st.subheader("1. Upload Data ODP")
    st.write("Pastikan file mengandung kolom: ODP_NAME, LATITUDE, LONGITUDE, AVAI, USED")
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
                odp_df = None
            else:
                st.success(f"Data ODP berhasil dibaca! {len(odp_df)} ODP ditemukan.")
                st.dataframe(odp_df[required_cols].head())
        except Exception as e:
            st.error(f"Error membaca data ODP: {str(e)}")
    
    # Upload data pelanggan
    st.subheader("2. Upload Data Pelanggan")
    st.write("File harus mengandung kolom latitude dan longitude (nama kolom fleksibel)")
    pelanggan_file = st.file_uploader("Pilih file Excel/CSV data pelanggan", type=['xlsx', 'xls', 'csv'], key="pelanggan_uploader")
    
    pelanggan_df = None
    if pelanggan_file is not None:
        try:
            if pelanggan_file.name.endswith('.csv'):
                pelanggan_df = pd.read_csv(pelanggan_file)
            else:
                pelanggan_df = pd.read_excel(pelanggan_file)
            
            st.success(f"Data pelanggan berhasil dibaca! {len(pelanggan_df)} pelanggan ditemukan.")
            
            # Deteksi kolom koordinat otomatis
            lat_col, lon_col = detect_coordinate_columns(pelanggan_df)
            
            st.write(f"Kolom terdeteksi: Latitude = '{lat_col}', Longitude = '{lon_col}'")
            
            # Konfirmasi kolom
            col1, col2 = st.columns(2)
            with col1:
                lat_col = st.selectbox("Konfirmasi kolom Latitude", pelanggan_df.columns, 
                                     index=list(pelanggan_df.columns).index(lat_col))
            with col2:
                lon_col = st.selectbox("Konfirmasi kolom Longitude", pelanggan_df.columns, 
                                     index=list(pelanggan_df.columns).index(lon_col))
            
            # Validasi data koordinat
            pelanggan_df[lat_col] = pd.to_numeric(pelanggan_df[lat_col], errors='coerce')
            pelanggan_df[lon_col] = pd.to_numeric(pelanggan_df[lon_col], errors='coerce')
            pelanggan_df = pelanggan_df.dropna(subset=[lat_col, lon_col])
            
            st.write("**Preview Data Pelanggan:**")
            st.dataframe(pelanggan_df.head())
        except Exception as e:
            st.error(f"Error membaca data pelanggan: {str(e)}")
    
    # Proses rekomendasi
    if odp_df is not None and pelanggan_df is not None:
        st.subheader("3. Hasil Rekomendasi ODP")
        
        if st.button("Proses Rekomendasi"):
            with st.spinner('Menghitung rekomendasi ODP terdekat...'):
                # Hitung ODP terdekat untuk setiap pelanggan
                results = pelanggan_df.apply(
                    lambda row: calculate_distance_and_flag(row, odp_df, lat_col, lon_col), 
                    axis=1
                )
                
                # Gabungkan hasil dengan data pelanggan asli
                final_df = pd.concat([pelanggan_df, results], axis=1)
                
                # Hitung statistik
                stat_df = pd.DataFrame({
                    'Kategori': ['ODP Tersedia', 'Potensi PT2/PT3', 'Tidak Ada ODP'],
                    'Jumlah': [
                        len(final_df[final_df['STATUS_REKOMENDASI'] == 'ODP Tersedia']),
                        len(final_df[final_df['STATUS_REKOMENDASI'] == 'Potensi PT2/PT3']),
                        len(final_df[final_df['STATUS_REKOMENDASI'] == 'Tidak Ada ODP'])
                    ]
                })
                
                st.success("**Hasil Analisis:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("ODP Tersedia", stat_df[stat_df['Kategori'] == 'ODP Tersedia']['Jumlah'].values[0])
                with col2:
                    st.metric("Potensi PT2/PT3", stat_df[stat_df['Kategori'] == 'Potensi PT2/PT3']['Jumlah'].values[0])
                with col3:
                    st.metric("Tidak Ada ODP", stat_df[stat_df['Kategori'] == 'Tidak Ada ODP']['Jumlah'].values[0])
                
                # Tampilkan hasil
                st.write("**Detail Rekomendasi:**")
                st.dataframe(final_df)
                
                # Download hasil
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    final_df.to_excel(writer, index=False, sheet_name='Rekomendasi')
                    stat_df.to_excel(writer, index=False, sheet_name='Statistik')
                    odp_df.to_excel(writer, index=False, sheet_name='Data_ODP')
                
                st.download_button(
                    label="Unduh Hasil Lengkap (Excel)",
                    data=output.getvalue(),
                    file_name='rekomendasi_odp_fleksibel.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

if __name__ == "__main__":
    main()
