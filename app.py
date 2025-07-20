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

st.markdown("## 📑 Rename Bukti Potong PPh Unifikasi Berdasarkan Metadata")
st.markdown("*By: Reza Fahlevi Lubis BKP @zavibis*")

st.markdown("### 📌 Petunjuk Penggunaan")
st.markdown("""
1. **Upload** satu atau beberapa file PDF Bukti Potong.
2. Aplikasi otomatis membaca metadata dari PDF.
3. Klik **Rename PDF & Download** untuk unduh ZIP berisi file PDF yang sudah dinamai ulang.
""")

def extract_safe(text, pattern, group=1, default=""):
    match = re.search(pattern, text)
    return match.group(group).strip() if match else default

def smart_extract_dpp_tarif_pph(text):
    for line in text.splitlines():
        if re.search(r"\b\d{2}-\d{3}-\d{2}\b", line):
            numbers = re.findall(r"\d[\d.]*", line)
            if len(numbers) >= 6:
                try:
                    dpp = int(numbers[3].replace(".", ""))
                    tarif = int(numbers[4])
                    pph = int(numbers[5].replace(".", ""))
                    return dpp, tarif, pph
                except:
                    continue
    return 0, 0, 0

def extract_data_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    try:
        data = {}
        data["NomorDokumen"] = extract_safe(text, r"Nomor Dokumen\s*:\s*(.+)")
        data["Nama"] = extract_safe(text, r"A\.2 NAMA\s*:\s*(.+)")
        data["NPWP"] = extract_safe(text, r"A\.1 NPWP / NIK\s*:\s*(\d+)")
        data["TanggalDokumen"] = extract_safe(text, r"Tanggal\s*:\s*(\d{2} .+ \d{4})")
        return data
    except:
        return None

def sanitize_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "_", str(text))

def generate_filename(data):
    parts = ["Bukti Potong"]
    for k in ["TanggalDokumen", "Nama", "NPWP", "NomorDokumen"]:
        parts.append(sanitize_filename(data.get(k, "-")))
    return "_".join(parts) + ".pdf"

uploaded_files = st.file_uploader("📎 Upload PDF Bukti Potong", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    data_rows = []
    for file in uploaded_files:
        result = extract_data_from_pdf(file)
        if result:
            result["original_name"] = file.name
            result["file_bytes"] = file.read()
            data_rows.append(result)

    if data_rows:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for row in data_rows:
                new_name = generate_filename(row)
                zipf.writestr(new_name, row["file_bytes"])
        zip_buffer.seek(0)
        st.success("✅ Rename selesai. Klik tombol di bawah untuk mengunduh.")
        st.download_button("📦 Download ZIP Bukti Potong", zip_buffer, file_name="bupot_renamed.zip", mime="application/zip")
