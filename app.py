
# Revisi ke-202507201230-1
# - Kolom NOMOR diganti "Nomor Bukti Potong"
# - Tambah kolom Masa, Tahun dari Masa Pajak

import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
import zipfile

st.set_page_config(page_title="Rename Bukti Potong Unifikasi", layout="centered")

st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
        color: white;
    }
    h1, h2, h3, h4, h5, h6, p, label, .markdown-text-container, .stText, .stMarkdown {
        color: white !important;
    }
    .stButton>button {
        color: white !important;
        background-color: #1f6feb;
        border-radius: 8px;
        padding: 0.5em 1em;
    }
    .stDownloadButton>button {
        background-color: #2ea44f;
        color: white !important;
        border-radius: 8px;
        padding: 0.5em 1em;
    }
    .stFileUploader {
        background-color: #161b22;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("## 🧾 Rename PDF Bukti Potong Berdasarkan Format yang ditentukan.")
st.markdown("*By: Reza Fahlevi Lubis BKP @zavibis*")

st.markdown("### 📌 Petunjuk Penggunaan")
st.markdown("""
1. **Upload** satu atau beberapa file PDF Bukti Potong.
2. Aplikasi akan membaca isi metadata dari setiap PDF.
3. Pilih dan urutkan **kolom-kolom metadata** untuk dijadikan format nama file PDF.
4. Klik **Rename PDF & Download** untuk mengunduh file hasil rename dalam 1 file ZIP.
""")

def extract_safe(text, pattern, group=1, default=""):
    match = re.search(pattern, text)
    return match.group(group).strip() if match else default

def extract_block(text, start_marker, end_marker):
    pattern = rf"{re.escape(start_marker)}(.*?){re.escape(end_marker)}"
    match = re.search(pattern, text, re.DOTALL)
    return match.group(1) if match else ""

def extract_data_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    data = {}
    try:
        data["Nomor Bukti Potong"] = extract_safe(text, r"\n(\S{9})\s+\d{2}-\d{4}")
        data["MASA PAJAK"] = extract_safe(text, r"\n\S{9}\s+(\d{2}-\d{4})")
        if "-" in data["MASA PAJAK"]:
            data["Masa"], data["Tahun"] = data["MASA PAJAK"].split("-")
        else:
            data["Masa"], data["Tahun"] = "", ""

        data["SIFAT PEMOTONGAN"] = extract_safe(text, r"(TIDAK FINAL|FINAL)")
        data["STATUS BUKTI"] = extract_safe(text, r"(NORMAL|PEMBETULAN)")
        data["NPWP / NIK PIHAK DIPOTONG"] = extract_safe(text, r"A\.1 NPWP / NIK\s*:\s*(\d+)")
        data["NAMA PIHAK DIPOTONG"] = extract_safe(text, r"A\.2 NAMA\s*:\s*(.+)")

        identitas_block = extract_block(text, "A. IDENTITAS WAJIB PAJAK YANG DIPOTONG DAN/ATAU DIPUNGUT PPh ATAU PENERIMA PENGHASILAN", "B. PEMOTONGAN")
        data["NOMOR IDENTITAS TEMPAT KEGIATAN USAHA"] = extract_safe(identitas_block, r"(\d{15,})")

        data["JENIS PPH"] = extract_safe(text, r"B\.2 Jenis PPh\s*:\s*(Pasal \d+)")
        data["KODE OBJEK PAJAK"] = extract_safe(text, r"(\d{2}-\d{3}-\d{2})")
        data["OBJEK PAJAK"] = extract_safe(text, r"\d{2}-\d{3}-\d{2}\s+([A-Za-z ]+)")
        data["DPP"] = extract_safe(text, r"(\d{1,3}(\.\d{3})*)\s+\d{1,2}\s+(\d{1,3}(\.\d{3})*)", 1)
        data["TARIF %"] = extract_safe(text, r"(\d{1,3}(\.\d{3})*)\s+(\d{1,2})\s+(\d{1,3}(\.\d{3})*)", 3)
        data["PAJAK PENGHASILAN"] = extract_safe(text, r"(\d{1,3}(\.\d{3})*)\s+\d{1,2}\s+(\d{1,3}(\.\d{3})*)", 3)
        data["JENIS DOKUMEN"] = extract_safe(text, r"Jenis Dokumen\s*:\s*(.+)")
        data["TANGGAL DOKUMEN"] = extract_safe(text, r"Tanggal\s*:\s*(\d{2} .+ \d{4})")
        data["NOMOR DOKUMEN"] = extract_safe(text, r"Nomor Dokumen\s*:\s*(.+)")

        pemotong_block = extract_block(text, "C. IDENTITAS PEMOTONG DAN/ATAU PEMUNGUT PPh", "D. TANDA TANGAN")
        data["NPWP / NIK PEMOTONG"] = extract_safe(pemotong_block, r"C\.1 NPWP / NIK\s*:\s*(\d+)")
        data["NAMA PEMOTONG"] = extract_safe(pemotong_block, r"C\.3.*?:\s*(.+)")
        data["NITKU PEMOTONG"] = extract_safe(pemotong_block, r"(\d{15,})")
        data["TANGGAL PEMOTONGAN"] = extract_safe(pemotong_block, r"C\.4 TANGGAL\s*:\s*(\d{2} .+ \d{4})")
        data["PENANDATANGAN PEMOTONG"] = extract_safe(pemotong_block, r"C\.5 NAMA PENANDATANGAN\s*:\s*(.+)")

        return data
    except Exception as e:
        st.warning(f"Gagal ekstrak data: {e}")
        return None

def sanitize_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "_", str(text))

def generate_filename(row, selected_cols):
    parts = [sanitize_filename(str(row[col])) for col in selected_cols]
    return "Bukti Potong " + "_".join(parts) + ".pdf"

uploaded_files = st.file_uploader("📎 Upload PDF Bukti Potong", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    data_rows = []
    for uploaded_file in uploaded_files:
        with st.spinner(f"📄 Membaca {uploaded_file.name}..."):
            raw_data = extract_data_from_pdf(uploaded_file)
            if raw_data:
                raw_data["OriginalName"] = uploaded_file.name
                raw_data["FileBytes"] = uploaded_file.read()
                data_rows.append(raw_data)

    if data_rows:
        df = pd.DataFrame(data_rows).drop(columns=["FileBytes", "OriginalName"])
        column_options = df.columns.tolist()
        selected_columns = st.multiselect("### ✏️ Pilih Kolom untuk Format Nama File", column_options, default=[], key="formatselector")

        if st.button("🔁 Rename PDF & Download"):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for i, row in df.iterrows():
                    filename = generate_filename(row, selected_columns)
                    zipf.writestr(filename, data_rows[i]["FileBytes"])
            zip_buffer.seek(0)
            st.success("✅ Berhasil! Klik tombol di bawah ini untuk mengunduh file ZIP.")
            st.download_button("📦 Download ZIP Bukti Potong", zip_buffer, file_name="bukti_potong_renamed.zip", mime="application/zip")
