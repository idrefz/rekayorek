import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from io import BytesIO
import pydeck as pdk

st.set_page_config(page_title="Rekomendasi ODP dengan Flagging PT2/PT3", layout="wide")

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
        'ODP_LAT': best_odp['LATITUDE'] if best_odp is not None else None,
        'ODP_LON': best_odp['LONGITUDE'] if best_odp is not None else None,
        'ODP_AVAI': best_odp['AVAI'] if best_odp is not None else None,
        'ODP_USED': best_odp['USED'] if best_odp is not None else None,
        'ODP_IS_TOTAL': best_odp['IS_TOTAL'] if best_odp is not None else None,
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

def main():
    st.title("Rekomendasi ODP dengan Flagging Potensi PT2/PT3")
    st.write("""
    Aplikasi ini akan menganalisis data pelanggan dan ODP untuk memberikan rekomendasi ODP terdekat 
    dalam radius 200 meter dengan avail minimal 6, serta menandai area yang membutuhkan PT2/PT3.
    """)
    
    # Upload data ODP
    st.subheader("1. Upload Data ODP")
    st.write("Pastikan file mengandung kolom: ODP_NAME, LATITUDE, LONGITUDE, IS_TOTAL, AVAI, USED")
    odp_file = st.file_uploader("Pilih file Excel/CSV data ODP", type=['xlsx', 'xls', 'csv'], key="odp_uploader")
    
    odp_df = None
    if odp_file is not None:
        try:
            if odp_file.name.endswith('.csv'):
                odp_df = pd.read_csv(odp_file)
            else:
                odp_df = pd.read_excel(odp_file)
            
            # Validasi kolom penting
            required_cols = ['ODP_NAME', 'LATITUDE', 'LONGITUDE', 'IS_TOTAL', 'AVAI', 'USED']
            missing_cols = [col for col in required_cols if col not in odp_df.columns]
            
            if missing_cols:
                st.error(f"Kolom penting tidak ditemukan: {', '.join(missing_cols)}")
                odp_df = None
            else:
                st.success(f"Data ODP berhasil dibaca! {len(odp_df)} ODP ditemukan.")
                
                # Tampilkan statistik ODP
                st.write("**Statistik ODP:**")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total ODP", len(odp_df))
                with col2:
                    st.metric("ODP dengan avail ≥6", len(odp_df[odp_df['AVAI'] >= 6]))
                with col3:
                    st.metric("ODP dengan avail <6", len(odp_df[odp_df['AVAI'] < 6]))
                
                # Tampilkan preview data
                st.dataframe(odp_df[required_cols].head())
                
                # Tampilkan peta ODP
                try:
                    st.write("**Peta Distribusi ODP:**")
                    st.pydeck_chart(pdk.Deck(
                        map_style='mapbox://styles/mapbox/light-v9',
                        initial_view_state=pdk.ViewState(
                            latitude=odp_df['LATITUDE'].mean(),
                            longitude=odp_df['LONGITUDE'].mean(),
                            zoom=11,
                            pitch=50,
                        ),
                        layers=[
                            pdk.Layer(
                                'ScatterplotLayer',
                                data=odp_df,
                                get_position='[LONGITUDE, LATITUDE]',
                                get_color='[200, 30, 0, 160]',
                                get_radius=100,
                                pickable=True
                            ),
                            pdk.Layer(
                                'ScatterplotLayer',
                                data=odp_df[odp_df['AVAI'] >= 6],
                                get_position='[LONGITUDE, LATITUDE]',
                                get_color='[0, 200, 30, 160]',
                                get_radius=100,
                                pickable=True
                            )
                        ],
                        tooltip={
                            "html": "<b>ODP:</b> {ODP_NAME}<br/>"
                                   "<b>Avail:</b> {AVAI}<br/>"
                                   "<b>Used:</b> {USED}",
                            "style": {
                                "backgroundColor": "steelblue",
                                "color": "white"
                            }
                        }
                    ))
                except Exception as e:
                    st.warning(f"Tidak dapat menampilkan peta ODP: {str(e)}")
    
    # Upload data pelanggan
    st.subheader("2. Upload Data Pelanggan")
    st.write("Pastikan file mengandung kolom latitude dan longitude pelanggan")
    pelanggan_file = st.file_uploader("Pilih file Excel/CSV data pelanggan", type=['xlsx', 'xls', 'csv'], key="pelanggan_uploader")
    
    pelanggan_df = None
    if pelanggan_file is not None:
        try:
            if pelanggan_file.name.endswith('.csv'):
                pelanggan_df = pd.read_csv(pelanggan_file)
            else:
                pelanggan_df = pd.read_excel(pelanggan_file)
            
            st.success(f"Data pelanggan berhasil dibaca! {len(pelanggan_df)} pelanggan ditemukan.")
            
            # Pilih kolom koordinat
            cols = pelanggan_df.columns.tolist()
            col1, col2 = st.columns(2)
            with col1:
                lat_col = st.selectbox("Pilih kolom Latitude pelanggan", cols, 
                                      index=cols.index('latitude') if 'latitude' in cols else 0)
            with col2:
                lon_col = st.selectbox("Pilih kolom Longitude pelanggan", cols, 
                                      index=cols.index('longitude') if 'longitude' in cols else 1 if len(cols) > 1 else 0)
            
            # Validasi data koordinat
            pelanggan_df[lat_col] = pd.to_numeric(pelanggan_df[lat_col], errors='coerce')
            pelanggan_df[lon_col] = pd.to_numeric(pelanggan_df[lon_col], errors='coerce')
            pelanggan_df = pelanggan_df.dropna(subset=[lat_col, lon_col])
            
            st.dataframe(pelanggan_df.head())
            
            # Tampilkan peta pelanggan
            try:
                st.write("**Peta Distribusi Pelanggan:**")
                st.map(pelanggan_df.rename(columns={
                    lat_col: 'lat',
                    lon_col: 'lon'
                }))
            except:
                st.warning("Tidak dapat menampilkan peta pelanggan")
    
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
                st.dataframe(final_df)
                
                # Buat peta interaktif
                try:
                    st.write("**Peta Rekomendasi:**")
                    
                    # Siapkan data untuk peta
                    map_df = final_df.copy()
                    map_df['lat'] = map_df[lat_col]
                    map_df['lon'] = map_df[lon_col]
                    
                    # Warna berdasarkan status
                    color_map = {
                        'ODP Tersedia': [0, 255, 0, 160],    # Hijau
                        'Potensi PT2/PT3': [255, 165, 0, 160], # Orange
                        'Tidak Ada ODP': [255, 0, 0, 160]     # Merah
                    }
                    map_df['color'] = map_df['STATUS_REKOMENDASI'].map(color_map)
                    
                    # Buat peta dengan PyDeck
                    st.pydeck_chart(pdk.Deck(
                        map_style='mapbox://styles/mapbox/light-v9',
                        initial_view_state=pdk.ViewState(
                            latitude=map_df['lat'].mean(),
                            longitude=map_df['lon'].mean(),
                            zoom=11,
                            pitch=50,
                        ),
                        layers=[
                            pdk.Layer(
                                'ScatterplotLayer',
                                data=map_df,
                                get_position='[lon, lat]',
                                get_color='color',
                                get_radius=50,
                                pickable=True
                            ),
                            pdk.Layer(
                                'ScatterplotLayer',
                                data=odp_df[odp_df['AVAI'] >= 6],
                                get_position='[LONGITUDE, LATITUDE]',
                                get_color='[0, 0, 255, 160]',
                                get_radius=100,
                                pickable=True
                            )
                        ],
                        tooltip={
                            "html": "<b>Status:</b> {STATUS_REKOMENDASI}<br/>"
                                   "<b>Keterangan:</b> {KETERANGAN}<br/>"
                                   "<b>ODP Terdekat:</b> {ODP_TERDEKAT}<br/>"
                                   "<b>Jarak:</b> {JARAK_METER} meter",
                            "style": {
                                "backgroundColor": "steelblue",
                                "color": "white"
                            }
                        }
                    ))
                except Exception as e:
                    st.warning(f"Tidak dapat menampilkan peta interaktif: {str(e)}")
                
                # Download hasil
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    final_df.to_excel(writer, index=False, sheet_name='Rekomendasi')
                    
                    # Buat worksheet tambahan dengan statistik
                    stat_df.to_excel(writer, index=False, sheet_name='Statistik')
                    
                    # Buat worksheet dengan data ODP
                    odp_df.to_excel(writer, index=False, sheet_name='Data_ODP')
                
                st.download_button(
                    label="Unduh Hasil Lengkap (Excel)",
                    data=output.getvalue(),
                    file_name='rekomendasi_odp_dengan_flagging.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

if __name__ == "__main__":
    main()
