import sys
from pathlib import Path

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


setup_page("Xác thực SHA-256", "🔒")
page_header(
    "Xác thực SHA-256",
    "Nhập SHA-256 hoặc một phần mã giao dịch để kiểm tra tính toàn vẹn ảnh bằng chứng.",
)

df = normalize_df(load_violations())

if df.empty:
    st.info("Chưa có dữ liệu vi phạm.")
    st.stop()

hash_input = st.text_input("Nhập SHA-256")

if st.button("Kiểm tra", type="primary"):
    if not hash_input.strip():
        st.warning("Vui lòng nhập SHA-256 hoặc mã giao dịch.")
        st.stop()

    query = hash_input.strip().lower()
    matches = df[
        df["image_hash"].fillna("").str.lower().str.contains(query, regex=False)
        | df["blockchain_tx"].fillna("").str.lower().str.contains(query, regex=False)
    ]

    if matches.empty:
        st.markdown('<div class="bad-result">MISMATCH</div>', unsafe_allow_html=True)
        st.caption("Không tìm thấy bản ghi có SHA-256 hoặc Blockchain TX tương ứng.")
        st.stop()

    for _, row in matches.iterrows():
        image_path = resolve_image_path(row["image_path"])
        stored_hash = str(row.get("image_hash") or "")
        current_hash = ""

        st.divider()
        st.write(f"**ID:** {row['id']}")
        st.write(f"**Thời gian:** {row['display_time']}")

        if not image_path.exists():
            st.markdown('<div class="bad-result">MISMATCH</div>', unsafe_allow_html=True)
            st.caption(f"Không tìm thấy ảnh: {image_path}")
            continue

        current_hash = calculate_sha256(image_path)
        if stored_hash and current_hash == stored_hash:
            st.markdown('<div class="ok-result">MATCH</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="bad-result">MISMATCH</div>', unsafe_allow_html=True)

        st.image(str(image_path), caption="Ảnh bằng chứng", width="stretch")
        st.write("**SHA-256 lưu trong DB**")
        st.code(stored_hash)
        st.write("**SHA-256 tính lại từ ảnh**")
        st.code(current_hash)
        st.write("**Blockchain TX**")
        st.code(str(row.get("blockchain_tx") or ""))
