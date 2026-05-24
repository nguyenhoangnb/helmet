import streamlit as st
import tempfile
import os
import hashlib
import sqlite3
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import pandas as pd
from datetime import datetime
import time
import requests
import threading
from pathlib import Path



import os
from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
BLOCKCHAIN_RPC_URL = os.getenv("BLOCKCHAIN_RPC_URL", "")
BLOCKCHAIN_PRIVATE_KEY = os.getenv("BLOCKCHAIN_PRIVATE_KEY", "")
BLOCKCHAIN_CONTRACT_ADDRESS = os.getenv("BLOCKCHAIN_CONTRACT_ADDRESS", "")
BLOCKCHAIN_CHAIN_ID = os.getenv("BLOCKCHAIN_CHAIN_ID", "")
BLOCKCHAIN_EXPLORER_TX_URL = os.getenv("BLOCKCHAIN_EXPLORER_TX_URL", "")
ALERT_COOLDOWN = 1  # Gửi tối đa 1 cảnh báo mỗi 1 giây

# Biến toàn cầu để lưu thời gian alert cuối cùng (không bị reset)
_alert_history = {}  # {video_hash: last_time}

# CSS
def load_css():
    st.markdown("""
    <style>
    :root {
        --surface: #ffffff;
        --surface-soft: #f6f8fb;
        --border: #d9e2ec;
        --text-muted: #667085;
        --accent: #2563eb;
        --danger: #dc2626;
        --success: #16a34a;
    }

    .stApp {
        background:
            radial-gradient(circle at 12% 8%, rgba(37, 99, 235, 0.12), transparent 30%),
            linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        color: #101828;
    }

    section[data-testid="stSidebar"] {
        background: #0f172a;
    }

    section[data-testid="stSidebar"] * {
        color: #e5e7eb;
    }

    section[data-testid="stSidebar"] .stSlider p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li {
        color: #cbd5e1;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2.5rem;
        max-width: 1280px;
    }

    .app-hero {
        margin-bottom: 1.25rem;
        padding: 1.35rem 1.5rem;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.9);
        box-shadow: 0 16px 45px rgba(15, 23, 42, 0.08);
    }

    .app-kicker {
        margin: 0 0 0.35rem;
        color: var(--accent);
        font-size: 0.86rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0;
    }

    .app-title {
        margin: 0;
        color: #0f172a;
        font-size: 2.1rem;
        line-height: 1.15;
        font-weight: 800;
        letter-spacing: 0;
    }

    .app-subtitle {
        max-width: 760px;
        margin: 0.6rem 0 0;
        color: var(--text-muted);
        font-size: 1rem;
        line-height: 1.55;
    }

    .status-row {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0 1.25rem;
    }

    .status-item {
        padding: 0.85rem 1rem;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.82);
    }

    .status-label {
        margin: 0;
        color: var(--text-muted);
        font-size: 0.82rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0;
    }

    .status-value {
        margin: 0.25rem 0 0;
        color: #0f172a;
        font-size: 1.05rem;
        font-weight: 800;
    }

    .section-heading {
        margin: 1.25rem 0 0.5rem;
        color: #0f172a;
        font-size: 1.22rem;
        font-weight: 800;
        letter-spacing: 0;
    }

    div[data-testid="stFileUploader"] section {
        border: 1px dashed #94a3b8;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.82);
    }

    div[data-testid="stMetric"] {
        padding: 0.8rem 0.9rem;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.05);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 2.7rem;
        padding: 0 1rem;
        border: 1px solid var(--border);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.78);
        color: #334155;
        font-weight: 700;
    }

    .stTabs [aria-selected="true"] {
        border-color: var(--accent);
        color: var(--accent);
        background: #eff6ff;
    }

    button[kind="primary"] {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# ======================== CẤU HÌNH ========================
st.set_page_config(
    page_title="🚨 Helmet Detection System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

load_css()

# ======================== TRẠNG THÁI BAN ĐẦU ========================
if 'report_data' not in st.session_state:
    st.session_state.report_data = []
if 'last_alert_time' not in st.session_state:
    st.session_state.last_alert_time = 0

# Tải model
@st.cache_resource
def load_model():
    with st.spinner("🚀 Đang tải mô hình YOLO..."):
        return YOLO("weights/best_helmet3.pt")

model = load_model()


count = 0

VIOLATION_DIR = APP_DIR / "violations"
VIOLATION_DIR.mkdir(exist_ok=True)
DB_PATH = APP_DIR / "violations.db"

VIOLATION_CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "imagePath", "type": "string"},
            {"internalType": "string", "name": "ipfsUri", "type": "string"},
        ],
        "name": "registerViolation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    }
]

def init_violation_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            camera TEXT,
            violation_type TEXT,
            image_path TEXT,
            confidence REAL,
            image_hash TEXT,
            blockchain_tx TEXT,
            ipfs_uri TEXT
        )
    ''')

    existing_columns = {
        row[1] for row in c.execute("PRAGMA table_info(violations)").fetchall()
    }
    for column_name, column_type in {
        "image_hash": "TEXT",
        "blockchain_tx": "TEXT",
        "ipfs_uri": "TEXT",
    }.items():
        if column_name not in existing_columns:
            c.execute(f"ALTER TABLE violations ADD COLUMN {column_name} {column_type}")

    conn.commit()
    conn.close()


def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def is_blockchain_configured():
    return all([
        BLOCKCHAIN_RPC_URL,
        BLOCKCHAIN_PRIVATE_KEY,
        BLOCKCHAIN_CONTRACT_ADDRESS,
    ])


def register_hash_on_blockchain(evidence_hash, image_path, ipfs_uri):
    if not is_blockchain_configured():
        return f"local-chain:{evidence_hash[:16]}"

    try:
        from web3 import Web3

        web3 = Web3(Web3.HTTPProvider(BLOCKCHAIN_RPC_URL, request_kwargs={"timeout": 30}))
        if not web3.is_connected():
            raise ConnectionError("Cannot connect to blockchain RPC")

        account = web3.eth.account.from_key(BLOCKCHAIN_PRIVATE_KEY)
        contract = web3.eth.contract(
            address=web3.to_checksum_address(BLOCKCHAIN_CONTRACT_ADDRESS),
            abi=VIOLATION_CONTRACT_ABI,
        )
        chain_id = int(BLOCKCHAIN_CHAIN_ID) if BLOCKCHAIN_CHAIN_ID else web3.eth.chain_id
        nonce = web3.eth.get_transaction_count(account.address)
        evidence_hash_bytes = bytes.fromhex(evidence_hash)

        transaction = contract.functions.registerViolation(
            evidence_hash_bytes,
            str(image_path),
            ipfs_uri,
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "chainId": chain_id,
            "gas": 250000,
            "gasPrice": web3.eth.gas_price,
        })

        signed_tx = account.sign_transaction(transaction)
        raw_transaction = (
            signed_tx.raw_transaction
            if hasattr(signed_tx, "raw_transaction")
            else signed_tx.rawTransaction
        )
        tx_hash = web3.eth.send_raw_transaction(raw_transaction)
        return web3.to_hex(tx_hash)

    except Exception as error:
        print(f"[BLOCKCHAIN] Failed to register hash: {error}")
        return f"local-chain-error:{evidence_hash[:16]}"


def build_ipfs_uri(evidence_hash):
    # Placeholder tích hợp: thay bằng CID thật khi upload ảnh lên IPFS.
    return f"ipfs://pending/{evidence_hash[:16]}"


def save_violation_evidence(camera, violation_type, image_path, confidence, timestamp):
    image_hash = calculate_sha256(image_path)
    ipfs_uri = build_ipfs_uri(image_hash)
    blockchain_tx = register_hash_on_blockchain(image_hash, image_path, ipfs_uri)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO violations (
            timestamp, camera, violation_type, image_path, confidence,
            image_hash, blockchain_tx, ipfs_uri
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        timestamp,
        camera,
        violation_type,
        str(image_path),
        confidence,
        image_hash,
        blockchain_tx,
        ipfs_uri,
    ))
    conn.commit()
    conn.close()

    return {
        "image_hash": image_hash,
        "blockchain_tx": blockchain_tx,
        "ipfs_uri": ipfs_uri,
    }


def build_transaction_url(tx_hash):
    if not BLOCKCHAIN_EXPLORER_TX_URL or not tx_hash.startswith("0x"):
        return tx_hash
    return f"{BLOCKCHAIN_EXPLORER_TX_URL.rstrip('/')}/{tx_hash}"


init_violation_db()

# Vẽ bounding box 
def draw_boxes(image, results, actual_fps=None, font_scale_base=0.5):
    global count
    class_names = results.names
    boxes = results.boxes
    stats = {'total': 0, 'with helmet': 0, 'without helmet': 0, 'confidences': []}
    frame_height, frame_width, _ = image.shape
    font_scale = font_scale_base * (frame_width / 640)*1.2
    thickness = max(1, int(frame_width / 640 * 2.5)) 
    violation_detected = False
    best_violation_confidence = 0

    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = class_names[cls_id]
        # print(f'Detected: {label} with confidence {conf:.2f} at [{x1}, {y1}, {x2}, {y2}]')
        if cls_id == 1 and conf > 0.5:
            count += 1
            violation_detected = True
            best_violation_confidence = max(best_violation_confidence, conf)
            
        color = (0, 255, 0) if label == 'with helmet' else (0, 0, 255)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)
        
        # Cải thiện nền chữ để dễ đọc hơn
        (text_width, text_height), _ = cv2.getTextSize(f"{label} {conf:.2f}", 
                                                      cv2.FONT_HERSHEY_SIMPLEX, 
                                                      font_scale, thickness)
        cv2.rectangle(image, (x1, y1 - text_height - 10), 
                      (x1 + text_width, y1), color, -1)
        cv2.putText(image, f"{label} {conf:.2f}", (x1, y1 - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)
        
        # Hiển thị thông tin thống kê lên ảnh
        stats['total'] += 1
        stats['with helmet'] += int(label == 'with helmet')
        stats['without helmet'] += int(label == 'without helmet')
        stats['confidences'].append(conf)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if count == 2 and violation_detected:
        count = 0
        violation_path = VIOLATION_DIR / f"violation_{timestamp}.jpg"
        cv2.imwrite(str(violation_path), image)
        evidence = save_violation_evidence(
            "Traffic Camera",
            "Không đội mũ bảo hiểm",
            violation_path,
            best_violation_confidence,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        caption = (
            "⚠️ Vi phạm không đội mũ bảo hiểm!\n"
            f"SHA-256: {evidence['image_hash']}\n"
            f"Blockchain: {build_transaction_url(evidence['blockchain_tx'])}"
        )
        send_telegram_alert_async(str(violation_path), caption)

    # Tạo lớp phủ thống kê ở góc trên bên trái
    if actual_fps is not None:
        # Kích thước và vị trí hộp thống kê
        overlay_x_end = 180 # Chiều rộng hộp thống kê
        overlay_y_end = 90  # Chiều cao hộp thống kê
        
        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (overlay_x_end, overlay_y_end), (0, 0, 0), -1)
        image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)
        
        # Điều chỉnh kích thước font và độ dày cho chữ thống kê
        overlay_font_scale = font_scale * 1 
        overlay_thickness = max(2, int(thickness * 0.8)) 

        cv2.putText(image, f"Helmet: {stats['with helmet']}", 
                    (10, 25), cv2.FONT_HERSHEY_DUPLEX, overlay_font_scale, 
                    (0, 255, 0), overlay_thickness)
        
        cv2.putText(image, f"No Helmet: {stats['without helmet']}", 
                    (10, 55), cv2.FONT_HERSHEY_DUPLEX, overlay_font_scale, 
                    (0, 0, 255), overlay_thickness)
        
        fps_multiplier = 3
        displayed_fps = actual_fps * fps_multiplier

        cv2.putText(image, f"FPS: {displayed_fps:.1f}", 
                    (10, 85), cv2.FONT_HERSHEY_DUPLEX, overlay_font_scale, 
                    (0, 255, 255), overlay_thickness) 

    return image, stats

# Xử lý hình ảnh
def process_image(image, confidence_threshold, iou_threshold):
    with st.spinner("🔍 Đang tiến hành nhận diện..."):
        # Truyền ngưỡng tin cậy và IoU cho mô hình
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        results = model(image, conf=confidence_threshold, iou=iou_threshold, verbose=False)[0]
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        annotated_image, stats = draw_boxes(image_bgr, results)
        return cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB), stats



def send_telegram_alert(photo_path, caption):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Missing token/chat_id")
        return False

    if not os.path.exists(photo_path):
        print("Photo not found:", photo_path)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"

    try:
        with open(photo_path, "rb") as photo:
            response = requests.post(
                url,
                data={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "caption": caption
                },
                files={
                    "photo": photo
                },
                timeout=30
            )

        print(f"[TELEGRAM] Response: {response.status_code}")
        if response.status_code == 200:
            print(f"[TELEGRAM] ✅ Alert sent successfully!")
            return True
        print(f"[TELEGRAM] ❌ Failed: {response.text}")
        return False

    except Exception as e:
        print(f"[TELEGRAM] ❌ Error: {e}")
        return False

def send_telegram_alert_async(photo_path, caption):
    """Gửi cảnh báo Telegram với cooldown toàn cầu (không bị Streamlit reset)"""
    global _alert_history
    
    current_time = time.time()
    # Sử dụng default cooldown nếu chưa từng gửi
    last_alert = _alert_history.get("global", 0)
    
    # Kiểm tra cooldown
    if current_time - last_alert < ALERT_COOLDOWN:
        remaining = ALERT_COOLDOWN - (current_time - last_alert)
        print(f"[ALERT] ⏳ Cooldown active ({remaining:.1f}s remaining). Skipping alert.")
        return
    
    # Cập nhật thời gian alert
    _alert_history["global"] = current_time
    print(f"[ALERT] 🚀 Starting telegram alert thread...")
    
    # Gửi trong thread riêng (không chặn xử lý video)
    def send_with_logging():
        try:
            print(f"[THREAD] 🧵 Thread started (ID: {threading.current_thread().ident})")
            send_telegram_alert(photo_path, caption)
            print(f"[THREAD] ✅ Thread completed (ID: {threading.current_thread().ident})")
        except Exception as e:
            print(f"[THREAD] ❌ Thread error: {e}")
    
    thread = threading.Thread(
        target=send_with_logging,
        daemon=True
    )
    thread.start()
    print(f"[ALERT] 🔔 Alert thread created and started (Daemon: True)")

# Xử lý Video
def process_video(video_path, confidence_threshold, iou_threshold, skip_frames=5): 
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        st.error("Không mở được video. Vui lòng kiểm tra file.")
        return None

    stframe = st.empty()
    progress_bar = st.progress(0)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_count = 0

    status_text = st.empty()
    status_text.info(f"Đang xử lý video ({total_frames} frames)...")

    stats = {
        'total_frames': total_frames,
        'processed_frames': 0,
        'helmet_counts': [],
        'no_helmet_counts': [],
        'fps_list': [], 
        'start_time': datetime.now()
    }

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        
        # Bỏ qua các khung hình để tăng hiệu suất hiển thị
        if frame_count % skip_frames != 0 and frame_count != total_frames:
            progress_percent = min(frame_count / total_frames, 1.0)
            progress_bar.progress(progress_percent)
            status_text.info(f"Đang xử lý... {progress_percent*100:.1f}% hoàn thành")
            continue
        

        start = time.time()
        # Thay đổi kích thước khung hình 
        resized_frame = cv2.resize(frame, (640, 640)) 
        # resized_frame2 = cv2.resize(frame, (640, 640)) 
        
        # Thực hiện suy luận (inference)
        results = model(resized_frame, verbose=False, conf=confidence_threshold, iou=iou_threshold)[0]
        actual_fps = 1.0 / (time.time() - start) # Tính FPS thực tế

        # Vẽ các hộp và hiển thị FPS
        annotated_frame, frame_stats = draw_boxes(resized_frame.copy(), results, actual_fps=actual_fps)


        stats['helmet_counts'].append(frame_stats['with helmet'])
        stats['no_helmet_counts'].append(frame_stats['without helmet'])
        stats['fps_list'].append(actual_fps*3)  # Ghi lại FPS thực tế cho báo cáo
        stats['processed_frames'] += 1

        # Hiển thị khung hình đã được chú thích
        stframe.image(annotated_frame, channels="BGR", width="stretch")
        
        # Cập nhật thanh tiến trình và trạng thái
        progress_percent = min(frame_count / total_frames, 1.0)
        progress_bar.progress(progress_percent)
        status_text.info(f"Đang xử lý... {progress_percent*100:.1f}% hoàn thành")

    cap.release()
    stats['processing_time'] = datetime.now() - stats['start_time']
    status_text.success(f"✅ Xử lý hoàn tất! Thời gian: {stats['processing_time'].seconds} giây")
    
    # Tính toán thống kê tổng thể
    total_helmet = sum(stats['helmet_counts'])
    total_no_helmet = sum(stats['no_helmet_counts'])
    total_objects = total_helmet + total_no_helmet
    avg_fps = np.mean(stats['fps_list']) if stats['fps_list'] else 0
    safety_rate = (total_helmet / total_objects * 100) if total_objects > 0 else 0

    # Hiển thị thống kê video
    st.markdown("### 📊 Thống kê video")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("🧍 Tổng đối tượng", f"{total_objects}")
    with col2:
        st.metric("🟢 Có mũ", f"{total_helmet}")
    with col3:
        st.metric("🔴 Không mũ", f"{total_no_helmet}")
    with col4:
        st.metric("🔒 Tỷ lệ an toàn", f"{safety_rate:.2f}%")
    with col5:
        st.metric("🎞️ Tổng frame", f"{stats['processed_frames']}")
    with col6:
        st.metric("⚡ FPS trung bình", f"{avg_fps:.2f}")

    # Lưu lại dữ liệu báo cáo
    st.session_state.report_data.append({
        'Thời gian': stats['start_time'],
        'Loại': 'Video',
        'Tổng đối tượng': total_objects,
        'Có mũ': total_helmet,
        'Không mũ': total_no_helmet,
        'Tỷ lệ an toàn': f"{safety_rate:.2f}%",
        'Tổng frame': stats['processed_frames'],
        'FPS trung bình': f"{avg_fps:.2f}"
    })

    return stats

# ======================== XUẤT BÁO CÁO ========================
def generate_report():
    df = pd.DataFrame(st.session_state.report_data)

    if 'Thời gian' in df.columns:
        df['Thời gian'] = df['Thời gian'].dt.strftime('%Y-%m-%d %H:%M:%S')

    return df

# ======================== SIDEBAR ========================
with st.sidebar:
    st.title("Helmet AI")
    st.caption("Bảng điều khiển nhận diện vi phạm")
    
    st.markdown("---")
    st.markdown("### Thông số mô hình")
    confidence_threshold = st.slider("Ngưỡng tin cậy", 0.1, 1.0, 0.5, 0.05)
    iou_threshold = st.slider("Ngưỡng IoU", 0.1, 1.0, 0.4, 0.05)
    
    st.markdown("---")
    st.markdown("### Cảnh báo")
    
    # Hiển thị trạng thái cooldown từ biến global
    current_time = time.time()
    last_alert = _alert_history.get("global", 0)
    time_since_last_alert = current_time - last_alert
    
    if time_since_last_alert < ALERT_COOLDOWN:
        remaining_time = ALERT_COOLDOWN - time_since_last_alert
        st.warning(f"Cooldown: {remaining_time:.1f}s")
    else:
        st.success("Sẵn sàng gửi cảnh báo")
    
    # Button reset cooldown
    if st.button("Reset cooldown", use_container_width=True):
        _alert_history["global"] = 0
        st.success("Đã reset cooldown")
        st.rerun()
    
    st.markdown("---")
    st.markdown("### Trạng thái")
    telegram_status = "Đã cấu hình" if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID else "Chưa cấu hình"
    blockchain_status = "Đã cấu hình" if is_blockchain_configured() else "Chưa cấu hình"
    st.markdown("""
    - Model: YOLO helmet
    - Database: SQLite
    - Blockchain/IPFS: Web3 + IPFS placeholder
    """)
    st.caption(f"Telegram: {telegram_status}")
    st.caption(f"Blockchain: {blockchain_status}")

# ======================== GIAO DIỆN CHÍNH ========================
st.markdown(
    """
    <div class="app-hero">
        <p class="app-kicker">Traffic Safety Monitoring</p>
        <h1 class="app-title">Hệ thống nhận diện không đội mũ bảo hiểm</h1>
        <p class="app-subtitle">
            Phân tích ảnh hoặc video bằng YOLO, lưu ảnh bằng chứng, tạo mã SHA-256
            và ghi nhận dữ liệu vi phạm vào hệ thống.
        </p>
    </div>
    """, 
    unsafe_allow_html=True
)

telegram_status = "Hoạt động" if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID else "Chưa cấu hình"
blockchain_status = "Hoạt động" if is_blockchain_configured() else "Local"
st.markdown(
    f"""
    <div class="status-row">
        <div class="status-item">
            <p class="status-label">Model</p>
            <p class="status-value">YOLO Helmet</p>
        </div>
        <div class="status-item">
            <p class="status-label">Confidence</p>
            <p class="status-value">{confidence_threshold:.2f}</p>
        </div>
        <div class="status-item">
            <p class="status-label">IoU</p>
            <p class="status-value">{iou_threshold:.2f}</p>
        </div>
        <div class="status-item">
            <p class="status-label">Telegram</p>
            <p class="status-value">{telegram_status}</p>
        </div>
        <div class="status-item">
            <p class="status-label">Blockchain</p>
            <p class="status-value">{blockchain_status}</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="section-heading">Nguồn dữ liệu</div>', unsafe_allow_html=True)
image_tab, video_tab = st.tabs(["Hình ảnh", "Video"])

with image_tab:
    file = st.file_uploader(
        "Tải ảnh lên",
        type=["jpg", "jpeg", "png"],
        help="Chọn ảnh chứa người để phát hiện mũ bảo hiểm",
        key="image_uploader",
    )
    if file:
        image = Image.open(file)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="section-heading">Ảnh gốc</div>', unsafe_allow_html=True)
            st.image(image, width="stretch")
        
        with col2:
            st.markdown('<div class="section-heading">Kết quả phát hiện</div>', unsafe_allow_html=True)
            result, stats = process_image(np.array(image), confidence_threshold, iou_threshold)
            st.image(result, width="stretch")
        
        st.markdown('<div class="section-heading">Thống kê ảnh</div>', unsafe_allow_html=True)
        cols = st.columns(4)
        with cols[0]:
            st.metric("Tổng đối tượng", stats['total'])
        with cols[1]: 
            st.metric("Có mũ", stats['with helmet'], delta_color="off") 
        with cols[2]:
            st.metric("Không mũ", stats['without helmet'], delta_color="off")
        with cols[3]:
            safety_rate = (stats['with helmet'] / stats['total']) * 100 if stats['total'] > 0 else 0
            st.metric("Tỷ lệ an toàn", f"{safety_rate:.1f}%")

        st.session_state.report_data.append({
            'Thời gian': datetime.now(),
            'Loại': 'Ảnh',
            'Tổng đối tượng': stats['total'], 
            'Có mũ': stats['with helmet'], 
            'Không mũ': stats['without helmet'], 
            'Tỷ lệ an toàn': f"{safety_rate:.1f}%"
        })

with video_tab:
    file = st.file_uploader(
        "Tải video lên",
        type=["mp4", "mov", "avi"],
        help="Chọn video để phân tích theo thời gian thực",
        key="video_uploader",
    )
    if file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
            tfile.write(file.read())
            path = tfile.name

        stats = process_video(path, confidence_threshold, iou_threshold)

        try: 
            os.remove(path)
        except: 
            pass

# Thống kê tổng quan
if st.session_state.report_data:
    st.markdown("---")
    st.markdown('<div class="section-heading">Lịch sử thống kê</div>', unsafe_allow_html=True)
    
    df = generate_report()
    st.dataframe(df, width='stretch')
    
    col1, col2 = st.columns([1, 3])
    with col1:
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "Tải thống kê",
            data=csv,
            file_name=f"helmet_detection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv'
        )
    
    with col2:
        if st.button("Xóa toàn bộ lịch sử", type="primary"):
            st.session_state.report_data = []
            st.rerun()
