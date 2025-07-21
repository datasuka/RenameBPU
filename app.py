# Revisi ke-202507201240-1
# - Tambah petunjuk penggunaan
# - Warna tombol biru DJP (#0070C0)

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
        background-color: #0070C0;
        border-radius: 8px;
        padding: 0.5em 1em;
    }
    .stDownloadButton>button {
        background-color: #0070C0;
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

st.markdown("## 🧾 Rename PDF Bukti Potong Berdasarkan Metadata")
st.markdown("*By: Reza Fahlevi Lubis BKP @zavibis*")

st.markdown("### 📌 Petunjuk Penggunaan")
st.markdown("""
1. Klik **Browse files** untuk upload satu atau beberapa file **PDF Bukti Potong Unifikasi**.
2. Aplikasi akan membaca informasi dari setiap PDF (misalnya nama pemotong, masa pajak, dsb).
3. Pilih kolom mana saja yang ingin digunakan sebagai format penamaan file.
4. Klik **Rename PDF & Download**.
5. File hasil rename akan diunduh dalam 1 file **ZIP**.
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
        data["Nomor Bukti Potong"] = extract_safe(text, r"\n(\S{9})\s+\d{2}-\d{4}")
        masa_pajak = extract_safe(text, r"\n\S{9}\s+(\d{2}-\d{4})")
        data["MASA PAJAK"] = masa_pajak
        if "-" in masa_pajak:
            data["MASA"], data["TAHUN"] = masa_pajak.split("-")
        else:
            data["MASA"], data["TAHUN"] = "", ""

        data["SIFAT PEMOTONGAN"] = extract_safe(text, r"(TIDAK FINAL|FINAL)")
        data["STATUS BUKTI"] = extract_safe(text, r"(NORMAL|PEMBETULAN)")

        data["NPWP / NIK PENERIMA PENGHASILAN"] = extract_safe(text, r"A\.1 NPWP / NIK\s*:\s*(\d+)")
        data["NAMA PENERIMA PENGHASILAN"] = extract_safe(text, r"A\.2 NAMA\s*:\s*(.+)")
        data["NOMOR IDENTITAS TEMPAT KEGIATAN USAHA"] = extract_safe(text, r"A\.3 NOMOR IDENTITAS.*?:\s*(\d+)")

        data["JENIS PPH"] = extract_safe(text, r"B\.2 Jenis PPh\s*:\s*(Pasal \d+)")
        data["KODE OBJEK PAJAK"] = extract_safe(text, r"(\d{2}-\d{3}-\d{2})")
        data["OBJEK PAJAK"] = extract_safe(text, r"\d{2}-\d{3}-\d{2}\s+([A-Za-z ]+)")
        dpp, tarif, pph = smart_extract_dpp_tarif_pph(text)
        data["DPP"] = dpp
        data["TARIF %"] = tarif
        data["PAJAK PENGHASILAN"] = pph

        data["JENIS DOKUMEN"] = extract_safe(text, r"Jenis Dokumen\s*:\s*(.+)")
        data["TANGGAL DOKUMEN"] = extract_safe(text, r"Tanggal\s*:\s*(\d{2} .+ \d{4})")
        data["NOMOR DOKUMEN"] = extract_safe(text, r"Nomor Dokumen\s*:\s*(.+)")

        data["NPWP / NIK PEMOTONG"] = extract_safe(text, r"C\.1 NPWP / NIK\s*:\s*(\d+)")
        data["NOMOR IDENTITAS TEMPAT USAHA PEMOTONG"] = extract_safe(text, r"C\.2.*?:\s*(\d+)")
        data["NAMA PEMOTONG"] = extract_safe(text, r"C\.3 NAMA PEMOTONG.*?:\s*(.+)")
        data["TANGGAL PEMOTONGAN"] = extract_safe(text, r"C\.4 TANGGAL\s*:\s*(\d{2} .+ \d{4})")
        data["PENANDATANGAN PEMOTONG"] = extract_safe(text, r"C\.5 NAMA PENANDATANGAN\s*:\s*(.+)")
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
