import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from violation_ui import (
    dashboard_counts,
    load_violations,
    page_header,
    setup_page,
    stats_by_date,
)


setup_page("Thống kê", "📊")
page_header(
    "Thống kê theo ngày",
    "Biểu đồ tổng hợp số lượng vi phạm theo ngày từ cơ sở dữ liệu SQLite.",
)

df = load_violations()
counts = dashboard_counts(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Tổng số vi phạm", counts["total"])
col2.metric("Đã băm SHA-256", counts["hashed"])
col3.metric("Chưa băm SHA-256", counts["missing_hash"])
col4.metric("Giao dịch Blockchain", counts["blockchain"])

stats = stats_by_date(df)
if stats.empty:
    st.info("Chưa có dữ liệu thống kê.")
    st.stop()

st.bar_chart(stats.set_index("Ngày"))
st.dataframe(stats, width="stretch", hide_index=True)
