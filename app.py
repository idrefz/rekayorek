import streamlit as st
import pandas as pd
import numpy as np
from geopy.distance import geodesic
import io

st.set_page_config(layout="wide")
st.title("ODP Recommendation System")

def calculate_recommendation(row, odp_df, lat_col, lon_col, sto_column, min_avail, max_distance):
    pelanggan_coord = (row[lat_col], row[lon_col])
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

    if sto_column and sto_column in row:
        filtered_odp = odp_df[odp_df['STO'] == row[sto_column]]
    else:
        filtered_odp = odp_df

    filtered_odp = filtered_odp.copy()
    filtered_odp['distance'] = filtered_odp.apply(
        lambda x: geodesic(pelanggan_coord, (x['LATITUDE'], x['LONGITUDE'])).meters, axis=1)
    
    nearby_odp = filtered_odp[filtered_odp['distance'] <= max_distance]
    eligible_odp = nearby_odp[nearby_odp['AVAI'] - nearby_odp['USED'] >= min_avail]

    best_odp = eligible_odp.nsmallest(1, 'distance').squeeze() if not eligible_odp.empty else None
    closest_odp = filtered_odp.nsmallest(1, 'distance').squeeze() if not filtered_odp.empty else None

    rsv = None
    rsk = None
    is_total = None

    if best_odp is not None:
        rsv = best_odp.get('RSV')
        rsk = best_odp.get('RSK')
        is_total = best_odp.get('IS_TOTAL')
    elif closest_odp is not None:
        rsv = closest_odp.get('RSV')
        rsk = closest_odp.get('RSK')
        is_total = closest_odp.get('IS_TOTAL')

    result = {
        'Nama ODP Rekomendasi': best_odp['ODP_NAME'] if best_odp is not None else closest_odp['ODP_NAME'] if closest_odp is not None else None,
        'Jarak (meter)': round(min(filtered_odp['distance']), 2) if best_odp is not None or closest_odp is not None else None,
        'AVAI': best_odp['AVAI'] if best_odp is not None else closest_odp['AVAI'] if closest_odp is not None else None,
        'USED': best_odp['USED'] if best_odp is not None else closest_odp['USED'] if closest_odp is not None else None,
        'IDLE': best_odp['AVAI'] - best_odp['USED'] if best_odp is not None else closest_odp['AVAI'] - closest_odp['USED'] if closest_odp is not None else None,
        'RSV': rsv,
        'RSK': rsk,
        'IS_TOTAL': is_total,
        'Latitude ODP': best_odp['LATITUDE'] if best_odp is not None else closest_odp['LATITUDE'] if closest_odp is not None else None,
        'Longitude ODP': best_odp['LONGITUDE'] if best_odp is not None else closest_odp['LONGITUDE'] if closest_odp is not None else None,
        'Status': 'Ready PT1' if best_odp is not None else 'Potensi PT2/PT3',
        'ODP Terdekat (Jika tidak memenuhi kriteria)': closest_odp['ODP_NAME'] if best_odp is None and closest_odp is not None else None,
        'Jarak ODP Terdekat (meter)': round(geodesic(pelanggan_coord, (closest_odp['LATITUDE'], closest_odp['LONGITUDE'])).meters, 2) if best_odp is None and closest_odp is not None else None
    }

    return result

uploaded_odp = st.file_uploader("Upload File ODP (.xlsx or .csv)", type=["xlsx", "csv"])
uploaded_pelanggan = st.file_uploader("Upload File Pelanggan (.xlsx or .csv)", type=["xlsx", "csv"])

if uploaded_odp and uploaded_pelanggan:
    if uploaded_odp.name.endswith('xlsx'):
        odp_df = pd.read_excel(uploaded_odp)
    else:
        odp_df = pd.read_csv(uploaded_odp)

    if uploaded_pelanggan.name.endswith('xlsx'):
        pelanggan_df = pd.read_excel(uploaded_pelanggan)
    else:
        pelanggan_df = pd.read_csv(uploaded_pelanggan)

    lat_col = st.selectbox("Pilih kolom Latitude pelanggan", pelanggan_df.columns)
    lon_col = st.selectbox("Pilih kolom Longitude pelanggan", pelanggan_df.columns)
    nama_kolom = st.selectbox("Pilih kolom Nama pelanggan", pelanggan_df.columns)
    sto_col = st.selectbox("Pilih kolom STO pelanggan (opsional)", ['-'] + list(pelanggan_df.columns))

    min_avail = st.slider("Minimum AVAI - USED", 0, 8, 2)
    max_distance = st.slider("Jarak maksimum (meter)", 100, 500, 300)

    if st.button("Proses Rekomendasi"):
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

        # Gabungkan data hasil ke pelanggan_df
        if sto_col != '-':
            base_df = pelanggan_df[[nama_kolom, sto_col]]
        else:
            base_df = pelanggan_df[[nama_kolom]]

        final_df = pd.concat([base_df.reset_index(drop=True), results.reset_index(drop=True)], axis=1)

        st.success("Rekomendasi selesai diproses!")

        st.dataframe(final_df)

        # Tombol download hasil
        towrite = io.BytesIO()
        downloaded = final_df.to_excel(towrite, index=False, sheet_name='Rekomendasi')
        towrite.seek(0)

        st.download_button(
            label="📥 Download Hasil Rekomendasi",
            data=towrite,
            file_name="hasil_rekomendasi_odp.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
