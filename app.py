# Revisi ke-202507202241
# Rename PDF Bukti Potong Unifikasi

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

st.title("📄 Rename PDF Bukti Potong Unifikasi Berdasarkan Metadata")
st.markdown("*By: Reza Fahlevi Lubis BKP @zavibis*")

def extract_safe(text, pattern, group=1, default=""):
    match = re.search(pattern, text)
    return match.group(group).strip() if match else default

def extract_identitas_tempat_kegiatan(text):
    try:
        block = re.search(r"A\. IDENTITAS WAJIB PAJAK YANG DIPOTONG.*?(B\. PEMOTONGAN|C\. PEMOTONGAN)", text, re.DOTALL)
        if block:
            block_text = block.group(0)
            match = re.search(r"NOMOR IDENTITAS.*?:\s*(\d+)", block_text)
            return match.group(1) if match else ""
    except:
        pass
    return ""

def extract_data_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    try:
        data = {}
        data["NOMOR"] = extract_safe(text, r"\n(\S{9})\s+\d{2}-\d{4}")
        data["MASA PAJAK"] = extract_safe(text, r"\n\S{9}\s+(\d{2}-\d{4})")
        data["SIFAT PEMOTONGAN"] = extract_safe(text, r"(TIDAK FINAL|FINAL)")
        data["STATUS BUKTI"] = extract_safe(text, r"(NORMAL|PEMBETULAN)")
        data["NPWP / NIK PIHAK DIPOTONG"] = extract_safe(text, r"A\.1 NPWP / NIK\s*:\s*(\d+)")
        data["NAMA PIHAK DIPOTONG"] = extract_safe(text, r"A\.2 NAMA\s*:\s*(.+)")
        data["NOMOR IDENTITAS TEMPAT KEGIATAN USAHA"] = extract_identitas_tempat_kegiatan(text)
        data["JENIS PPH"] = extract_safe(text, r"B\.2 Jenis PPh\s*:\s*(Pasal \d+)")
        data["KODE OBJEK"] = extract_safe(text, r"(\d{2}-\d{3}-\d{2})")
        data["OBJEK PAJAK"] = extract_safe(text, r"\d{2}-\d{3}-\d{2}\s+([A-Za-z ]+)")
        data["TANGGAL DOKUMEN"] = extract_safe(text, r"Tanggal\s*:\s*(\d{2} .+ \d{4})")
        data["NOMOR DOKUMEN"] = extract_safe(text, r"Nomor Dokumen\s*:\s*(.+)")
        return data
    except Exception as e:
        st.warning(f"Gagal ekstrak data: {e}")
        return None

def sanitize_filename(text):
    return re.sub(r'[\/*?:"<>|]', "_", str(text))

def generate_filename(row, selected_cols):
    parts = [sanitize_filename(str(row[col])) for col in selected_cols]
    return "Bukti Potong " + "_".join(parts) + ".pdf"

uploaded_files = st.file_uploader("📎 Upload PDF Bukti Potong", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    data_rows = []
    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.read()
        with pdfplumber.open(BytesIO(file_bytes)) as pdf:
            text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
        data = extract_data_from_pdf(BytesIO(file_bytes))
        if data:
            data["OriginalName"] = uploaded_file.name
            data["FileBytes"] = file_bytes
            data_rows.append(data)

    if data_rows:
        df = pd.DataFrame(data_rows).drop(columns=["FileBytes", "OriginalName"])
        column_options = df.columns.tolist()

        st.markdown("### ✏️ Pilih Kolom untuk Format Nama File")
        selected_columns = st.multiselect("Urutan Nama File", options=column_options, default=[], help="Drag untuk ubah urutan")

        if st.button("🔁 Rename PDF & Download"):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for i, row in df.iterrows():
                    filename = generate_filename(row, selected_columns)
                    zipf.writestr(filename, data_rows[i]["FileBytes"])
            zip_buffer.seek(0)
            st.success("✅ Berhasil! Klik tombol di bawah ini untuk mengunduh file ZIP.")
            st.download_button("📦 Download ZIP Bukti Potong", zip_buffer, file_name="bukti_potong_renamed.zip", mime="application/zip")
