import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from violation_ui import (
    calculate_sha256,
    load_violations,
    normalize_df,
    page_header,
    resolve_image_path,
    setup_page,
)


setup_page("Danh sách vi phạm", "📋")
page_header(
    "Danh sách vi phạm",
    "Tra cứu toàn bộ bản ghi vi phạm, xem ảnh bằng chứng và thông tin blockchain theo từng ID.",
)

df = normalize_df(load_violations())

if df.empty:
    st.info("Chưa có dữ liệu vi phạm.")
    st.stop()

table_df = df[["id", "display_time", "violation_type", "confidence"]].copy()
table_df.columns = ["ID", "Thời gian", "Loại vi phạm", "Độ tin cậy"]
st.dataframe(table_df, width="stretch", hide_index=True)

st.markdown("### Xem chi tiết vi phạm")
selected_id = st.selectbox("Chọn vi phạm", df["id"].tolist())
selected_row = df[df["id"] == selected_id].iloc[0]

left_col, right_col = st.columns([1, 1])
image_path = resolve_image_path(selected_row["image_path"])

with left_col:
    if image_path.exists():
        st.image(str(image_path), caption=f"Ảnh bằng chứng ID {selected_id}", width="stretch")
    else:
        st.error(f"Không tìm thấy ảnh: {image_path}")

with right_col:
    st.markdown('<div class="detail-box">', unsafe_allow_html=True)
    st.write("**Thời gian**")
    st.write(selected_row["display_time"])
    st.write("**Loại vi phạm**")
    st.write(selected_row.get("violation_type", ""))
    st.write("**Độ tin cậy YOLO**")
    confidence = selected_row.get("confidence")
    st.write("" if pd.isna(confidence) else f"{float(confidence):.4f}")
    st.write("**SHA-256**")
    st.markdown(f'<div class="hash-text">{selected_row.get("image_hash") or ""}</div>', unsafe_allow_html=True)
    st.write("**Blockchain TX**")
    st.markdown(f'<div class="hash-text">{selected_row.get("blockchain_tx") or ""}</div>', unsafe_allow_html=True)
    st.write("**IPFS URI**")
    st.markdown(f'<div class="hash-text">{selected_row.get("ipfs_uri") or ""}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

if image_path.exists() and st.button("Tính lại SHA-256 ảnh này"):
    current_hash = calculate_sha256(image_path)
    stored_hash = str(selected_row.get("image_hash") or "")
    if current_hash == stored_hash:
        st.success("MATCH")
    else:
        st.error("MISMATCH")
    st.code(current_hash)

st.markdown("### Tìm kiếm theo hash")
search = st.text_input("Tìm theo hash")
if search:
    search_lower = search.lower()
    matches = df[
        df["image_hash"].fillna("").str.lower().str.contains(search_lower, regex=False)
        | df["blockchain_tx"].fillna("").str.lower().str.contains(search_lower, regex=False)
    ]

    if matches.empty:
        st.warning("Không tìm thấy bản ghi phù hợp.")
    else:
        for _, row in matches.iterrows():
            st.divider()
            col_img, col_info = st.columns([1, 2])
            result_image = resolve_image_path(row["image_path"])
            with col_img:
                if result_image.exists():
                    st.image(str(result_image), width="stretch")
                else:
                    st.caption("Không tìm thấy ảnh.")
            with col_info:
                st.write(f"**ID:** {row['id']}")
                st.write(f"**Thời gian:** {row['display_time']}")
                st.write("**Transaction Blockchain:**")
                st.markdown(f'<div class="hash-text">{row.get("blockchain_tx") or ""}</div>', unsafe_allow_html=True)
