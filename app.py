# Revisi ke-202507191810-1
# Rename PDF Bukti Potong Unifikasi Berdasarkan Metadata
# Tanpa ekspor Excel – hanya rename + UI urut kolom

import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
import zipfile

st.set_page_config(page_title="Rename Bukti Potong", layout="centered")

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

st.markdown("## 📄 Rename PDF Bukti Potong Unifikasi Berdasarkan Metadata")
st.markdown("*By: Reza Fahlevi Lubis BKP @zavibis*")

st.markdown("### 📌 Petunjuk Penggunaan")
st.markdown("""
1. Upload satu atau beberapa file PDF Bukti Potong.
2. Aplikasi akan membaca metadata dari isi PDF.
3. Pilih dan urutkan kolom metadata untuk dijadikan nama file.
4. Klik tombol untuk rename dan download hasil dalam 1 file ZIP.
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

def extract_data_from_pdf(file_stream):
    with pdfplumber.open(file_stream) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    data = {
        "NOMOR": extract_safe(text, r"\n(\S{9})\s+\d{2}-\d{4}"),
        "MASA": extract_safe(text, r"\n\S{9}\s+(\d{2}-\d{4})"),
        "SIFAT": extract_safe(text, r"(TIDAK FINAL|FINAL)"),
        "STATUS": extract_safe(text, r"(NORMAL|PEMBETULAN)"),
        "NPWP": extract_safe(text, r"A\.1 NPWP / NIK\s*:\s*(\d+)"),
        "NAMA": extract_safe(text, r"A\.2 NAMA\s*:\s*(.+)"),
        "JENIS_PPH": extract_safe(text, r"B\.2 Jenis PPh\s*:\s*(Pasal \d+)"),
        "OBJEK": extract_safe(text, r"(\d{2}-\d{3}-\d{2})"),
        "DOKUMEN": extract_safe(text, r"Nomor Dokumen\s*:\s*(.+)"),
    }
    return data

def sanitize_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "_", str(text).strip())

def generate_filename(row, selected_cols):
    parts = [sanitize_filename(row[col]) for col in selected_cols]
    return "Bukti Potong " + "_".join(parts) + ".pdf"

uploaded_files = st.file_uploader("📎 Upload Bukti Potong (PDF)", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    data_rows = []
    for file in uploaded_files:
        file_bytes = file.read()
        file_stream = BytesIO(file_bytes)
        try:
            data = extract_data_from_pdf(file_stream)
            data["OriginalName"] = file.name
            data["FileBytes"] = file_bytes
            data_rows.append(data)
        except:
            st.warning(f"Gagal membaca {file.name}")

    if data_rows:
        df = pd.DataFrame(data_rows).drop(columns=["FileBytes", "OriginalName"])
        column_options = df.columns.tolist()

        st.markdown("### ✏️ Pilih Kolom dan Urutkan Format Nama File")
        initial_df = pd.DataFrame({"Kolom": column_options})
        selected_rows = st.data_editor(
            initial_df,
            use_container_width=True,
            num_rows="dynamic",
            column_order=["Kolom"],
            column_config={
                "Kolom": st.column_config.SelectboxColumn(
                    "Pilih Kolom", options=column_options
                )
            },
            hide_index=True
        )
        selected_columns = selected_rows["Kolom"].dropna().tolist()

        if st.button("🔁 Rename PDF & Download"):
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for i, row in df.iterrows():
                    filename = generate_filename(row, selected_columns)
                    zipf.writestr(filename, data_rows[i]["FileBytes"])
            zip_buffer.seek(0)
            st.success("✅ Berhasil! Klik tombol di bawah ini untuk mengunduh ZIP.")
            st.download_button("📦 Download ZIP Hasil Rename", zip_buffer, file_name="bukti_potong_renamed.zip", mime="application/zip")
