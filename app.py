# Revisi Rename Bukti Potong Unifikasi v1
# - Rename PDF berdasarkan metadata
# - Tanpa export ke Excel
# - Siap deploy ke Streamlit & GitHub

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
</style>
""", unsafe_allow_html=True)

st.title("📑 Rename PDF Bukti Potong Unifikasi")
st.markdown("*By: Reza Fahlevi Lubis BKP @zavibis*")

st.markdown("### 📌 Petunjuk")
st.markdown("""
1. Upload satu atau beberapa file PDF Bukti Potong Unifikasi.
2. Aplikasi akan membaca metadata dari setiap file.
3. Pilih dan urutkan kolom untuk format nama file.
4. Klik tombol Rename untuk unduh file hasil rename.
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
        data["NOMOR"] = extract_safe(text, r"\n(\S{9})\s+\d{2}-\d{4}")
        data["MASA PAJAK"] = extract_safe(text, r"\n\S{9}\s+(\d{2}-\d{4})")
        data["SIFAT PEMOTONGAN"] = extract_safe(text, r"(TIDAK FINAL|FINAL)")
        data["STATUS BUKTI"] = extract_safe(text, r"(NORMAL|PEMBETULAN)")
        data["NPWP / NIK"] = extract_safe(text, r"A\.1 NPWP / NIK\s*:\s*(\d+)")
        data["NAMA"] = extract_safe(text, r"A\.2 NAMA\s*:\s*(.+)")
        data["NOMOR IDENTITAS TEMPAT USAHA"] = extract_safe(text, r"A\.3 NOMOR IDENTITAS.*?:\s*(\d+)")
        data["JENIS PPH"] = extract_safe(text, r"B\.2 Jenis PPh\s*:\s*(Pasal \d+)")
        data["KODE OBJEK"] = extract_safe(text, r"(\d{2}-\d{3}-\d{2})")
        data["OBJEK PAJAK"] = extract_safe(text, r"\d{2}-\d{3}-\d{2}\s+([A-Za-z ]+)")
        data["DPP"], data["TARIF %"], data["PAJAK PENGHASILAN"] = smart_extract_dpp_tarif_pph(text)
        data["JENIS DOKUMEN"] = extract_safe(text, r"Jenis Dokumen\s*:\s*(.+)")
        data["TANGGAL DOKUMEN"] = extract_safe(text, r"Tanggal\s*:\s*(\d{2} .+ \d{4})")
        data["NOMOR DOKUMEN"] = extract_safe(text, r"Nomor Dokumen\s*:\s*(.+)")
        data["NPWP / NIK PEMOTONG"] = extract_safe(text, r"C\.1 NPWP / NIK\s*:\s*(\d+)")
        data["NOMOR IDENTITAS TEMPAT USAHA PEMOTONG"] = extract_safe(text, r"C\.2.*?:\s*(\d+)")
        data["NAMA PEMOTONG"] = extract_safe(text, r"C\.3.*?:\s*(.+)")
        data["TANGGAL PEMOTONGAN"] = extract_safe(text, r"C\.4 TANGGAL\s*:\s*(\d{2} .+ \d{4})")
        data["NAMA PENANDATANGAN"] = extract_safe(text, r"C\.5 NAMA PENANDATANGAN\s*:\s*(.+)")
        return data
    except Exception as e:
        st.warning(f"Gagal ekstrak data: {e}")
        return None

uploaded_files = st.file_uploader("📎 Upload PDF Bukti Potong Unifikasi", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    for file in uploaded_files:
        result = extract_data_from_pdf(file)
        if result:
            result["OriginalName"] = file.name
            result["FileBytes"] = file.read()
            all_data.append(result)

    if all_data:
        df = pd.DataFrame(all_data).drop(columns=["FileBytes", "OriginalName"])
        column_options = df.columns.tolist()

        st.markdown("### ✏️ Pilih Kolom untuk Format Nama File")
        selected_columns = st.multiselect(
            "Urutan Nama File", column_options, default=[], help="Pilih kolom lalu geser untuk atur urutan"
        )

        if st.button("🔁 Rename PDF & Download"):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for i, row in df.iterrows():
                    name_parts = [str(row[col]).replace("/", "-") for col in selected_columns]
                    filename = "Bukti Potong " + "_".join(name_parts) + ".pdf"
                    zipf.writestr(filename, all_data[i]["FileBytes"])
            zip_buffer.seek(0)
            st.success("✅ Berhasil! Unduh file hasil rename:")
            st.download_button("📦 Download ZIP Bukti Potong", zip_buffer, file_name="bukti_potong_renamed.zip", mime="application/zip")
