import hashlib
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "violations.db"


def setup_page(title: str, icon: str = "🛡️") -> None:
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    load_css()
    render_sidebar_navigation()


def load_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --surface: #ffffff;
            --surface-soft: #f7f9fc;
            --border: #d8dee8;
            --text: #1f2937;
            --muted: #667085;
            --accent: #2563eb;
            --success: #16a34a;
            --danger: #dc2626;
        }

        .stApp {
            background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
            color: var(--text);
        }

        section[data-testid="stSidebar"] {
            background: #1f2937;
        }

        section[data-testid="stSidebar"] * {
            color: #e5e7eb;
        }

        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
            display: none;
        }

        section[data-testid="stSidebar"] [data-testid="stPageLink"] a {
            border-radius: 8px;
            color: #e5e7eb;
        }

        section[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
            background: #334155;
        }

        .block-container {
            max-width: 1280px;
            padding-top: 1.75rem;
            padding-bottom: 2.5rem;
        }

        .page-title {
            margin: 0 0 0.35rem;
            color: #1f2937;
            font-size: 2rem;
            line-height: 1.2;
            font-weight: 800;
            letter-spacing: 0;
        }

        .page-subtitle {
            max-width: 820px;
            margin: 0 0 1.25rem;
            color: var(--muted);
            font-size: 1rem;
            line-height: 1.55;
        }

        div[data-testid="stMetric"] {
            min-height: 108px;
            padding: 0.9rem 1rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.92);
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
        }

        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricValue"] {
            color: #334155;
        }

        .detail-box {
            padding: 0.9rem 1rem;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.92);
        }

        .hash-text {
            overflow-wrap: anywhere;
            word-break: break-word;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.88rem;
        }

        .ok-result {
            padding: 0.85rem 1rem;
            border: 1px solid rgba(22, 163, 74, 0.28);
            border-radius: 8px;
            background: #ecfdf3;
            color: #166534;
            font-weight: 800;
        }

        .bad-result {
            padding: 0.85rem 1rem;
            border: 1px solid rgba(220, 38, 38, 0.28);
            border-radius: 8px;
            background: #fef2f2;
            color: #991b1b;
            font-weight: 800;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <h1 class="page-title">{title}</h1>
        <p class="page-subtitle">{subtitle}</p>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_navigation() -> None:
    with st.sidebar:
        st.page_link("main.py", label="🏠 Dashboard")
        st.page_link("pages/2_Danh_sach_vi_pham.py", label="📋 Danh sách vi phạm")
        st.page_link("pages/3_Xac_thuc_SHA256.py", label="🔒 Xác thực SHA-256")
        st.page_link("pages/4_Thong_ke.py", label="📊 Thống kê")
        st.divider()


@st.cache_data(ttl=5)
def load_violations() -> pd.DataFrame:
    if not DB_PATH.exists():
        return pd.DataFrame(
            columns=[
                "id",
                "timestamp",
                "camera",
                "violation_type",
                "image_path",
                "confidence",
                "image_hash",
                "blockchain_tx",
                "ipfs_uri",
            ]
        )

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT * FROM violations ORDER BY id DESC",
            conn,
        )


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    normalized = df.copy()
    normalized["timestamp_dt"] = pd.to_datetime(
        normalized["timestamp"],
        errors="coerce",
    )
    normalized["date"] = normalized["timestamp_dt"].dt.date
    normalized["display_time"] = normalized["timestamp_dt"].dt.strftime("%d/%m/%Y %H:%M:%S")
    normalized["display_time"] = normalized["display_time"].fillna(normalized["timestamp"].astype(str))
    return normalized


def resolve_image_path(path_value) -> Path:
    raw_path = Path(str(path_value or ""))
    candidates = []

    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.extend(
            [
                APP_DIR / raw_path,
                APP_DIR.parent / raw_path,
                raw_path,
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else raw_path


def calculate_sha256(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def has_text(value) -> pd.Series:
    return value.notna() & (value.astype(str).str.strip() != "")


def dashboard_counts(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total": 0,
            "hashed": 0,
            "missing_hash": 0,
            "blockchain": 0,
            "today": 0,
        }

    normalized = normalize_df(df)
    image_hash = has_text(normalized["image_hash"])
    blockchain_tx = has_text(normalized["blockchain_tx"])
    today = pd.Timestamp.today().date()

    return {
        "total": int(len(normalized)),
        "hashed": int(image_hash.sum()),
        "missing_hash": int((~image_hash).sum()),
        "blockchain": int(blockchain_tx.sum()),
        "today": int((normalized["date"] == today).sum()),
    }


def stats_by_date(df: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_df(df)
    if normalized.empty:
        return pd.DataFrame(columns=["Ngày", "Số vi phạm"])

    dated = normalized.dropna(subset=["timestamp_dt"]).copy()
    dated["day"] = dated["timestamp_dt"].dt.date
    stats = (
        dated.groupby("day")["id"]
        .count()
        .reset_index()
        .sort_values("day")
    )
    stats["day"] = pd.to_datetime(stats["day"]).dt.strftime("%d/%m")
    stats.columns = ["Ngày", "Số vi phạm"]
    return stats


def render_dashboard() -> None:
    setup_page("Dashboard vi phạm", "🏠")
    page_header(
        "Dashboard thống kê",
        "Theo dõi số vi phạm, trạng thái băm SHA-256, giao dịch Blockchain và số vi phạm trong ngày.",
    )

    df = load_violations()
    counts = dashboard_counts(df)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Tổng số vi phạm", counts["total"])
    col2.metric("Đã băm SHA-256", counts["hashed"])
    col3.metric("Chưa băm SHA-256", counts["missing_hash"])
    col4.metric("Giao dịch Blockchain", counts["blockchain"])
    col5.metric("Vi phạm trong ngày", counts["today"])

    st.markdown("### Vi phạm gần nhất")
    normalized = normalize_df(df)
    if normalized.empty:
        st.info("Chưa có dữ liệu vi phạm.")
        return

    latest = normalized[
        ["id", "display_time", "violation_type", "confidence", "image_hash", "blockchain_tx"]
    ].head(10)
    latest.columns = [
        "ID",
        "Thời gian",
        "Loại vi phạm",
        "Độ tin cậy",
        "SHA-256",
        "Blockchain TX",
    ]
    st.dataframe(latest, width="stretch", hide_index=True)

    st.markdown("### Thống kê theo ngày")
    daily_stats = stats_by_date(df)
    if not daily_stats.empty:
        st.bar_chart(daily_stats.set_index("Ngày"))
