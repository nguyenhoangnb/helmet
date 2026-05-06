import streamlit as st
import tempfile
import os
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
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ALERT_COOLDOWN = 1  # Gửi tối đa 1 cảnh báo mỗi 1 giây

# ======================== CẤU HÌNH ========================
st.set_page_config(
    page_title="🚨 Helmet Detection System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================== TRẠNG THÁI BAN ĐẦU ========================
if 'report_data' not in st.session_state:
    st.session_state.report_data = []
if 'last_alert_time' not in st.session_state:
    st.session_state.last_alert_time = 0
if 'violation_count' not in st.session_state:
    st.session_state.violation_count = 0
if 'alert_history' not in st.session_state:
    st.session_state.alert_history = {}

# Tải model
@st.cache_resource
def load_model():
    with st.spinner("🚀 Đang tải mô hình YOLO..."):
        return YOLO("weights/best_helmet3.pt")

model = load_model()

VIOLATION_DIR = Path("violations")
VIOLATION_DIR.mkdir(exist_ok=True)


# ======================== GỬI TELEGRAM ========================
def send_telegram_alert(photo_path, caption):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM] Missing token/chat_id")
        return False

    if not os.path.exists(photo_path):
        print("[TELEGRAM] Photo not found:", photo_path)
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
                files={"photo": photo},
                timeout=30
            )
        print(f"[TELEGRAM] Response: {response.status_code}")
        if response.status_code == 200:
            print("[TELEGRAM] ✅ Alert sent successfully!")
            return True
        print(f"[TELEGRAM] ❌ Failed: {response.text}")
        return False

    except Exception as e:
        print(f"[TELEGRAM] ❌ Error: {e}")
        return False


def send_telegram_alert_async(photo_path, caption):
    """Gửi cảnh báo Telegram với cooldown lưu trong session_state"""
    current_time = time.time()
    last_alert = st.session_state.alert_history.get("global", 0)

    if current_time - last_alert < ALERT_COOLDOWN:
        remaining = ALERT_COOLDOWN - (current_time - last_alert)
        print(f"[ALERT] ⏳ Cooldown active ({remaining:.1f}s remaining). Skipping alert.")
        return

    st.session_state.alert_history["global"] = current_time
    print("[ALERT] 🚀 Starting telegram alert thread...")

    def send_with_logging():
        try:
            print(f"[THREAD] 🧵 Thread started (ID: {threading.current_thread().ident})")
            send_telegram_alert(photo_path, caption)
            print(f"[THREAD] ✅ Thread completed (ID: {threading.current_thread().ident})")
        except Exception as e:
            print(f"[THREAD] ❌ Thread error: {e}")

    thread = threading.Thread(target=send_with_logging, daemon=True)
    thread.start()
    print(f"[ALERT] 🔔 Alert thread created and started (Daemon: True)")


# ======================== VẼ BOUNDING BOX ========================
def draw_boxes(image, results, actual_fps=None, font_scale_base=0.5):
    class_names = results.names
    boxes = results.boxes
    stats = {'total': 0, 'with helmet': 0, 'without helmet': 0, 'confidences': []}
    frame_height, frame_width, _ = image.shape
    font_scale = font_scale_base * (frame_width / 640) * 1.2
    thickness = max(1, int(frame_width / 640 * 2.5))
    violation_detected = False

    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = class_names[cls_id]

        if cls_id == 1 and conf > 0.5:
            st.session_state.violation_count += 1
            violation_detected = True

        color = (0, 255, 0) if label == 'with helmet' else (0, 0, 255)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, thickness)

        (text_width, text_height), _ = cv2.getTextSize(
            f"{label} {conf:.2f}", cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        cv2.rectangle(image, (x1, y1 - text_height - 10),
                      (x1 + text_width, y1), color, -1)
        cv2.putText(image, f"{label} {conf:.2f}", (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness)

        stats['total'] += 1
        stats['with helmet'] += int(label == 'with helmet')
        stats['without helmet'] += int(label == 'without helmet')
        stats['confidences'].append(conf)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if st.session_state.violation_count >= 2 and violation_detected:
        st.session_state.violation_count = 0
        violation_path = VIOLATION_DIR / f"violation_{timestamp}.jpg"
        cv2.imwrite(str(violation_path), image)
        send_telegram_alert_async(str(violation_path), "⚠️ Vi phạm không đội mũ bảo hiểm!")

    # Lớp phủ thống kê ở góc trên bên trái
    if actual_fps is not None:
        overlay_x_end = 180
        overlay_y_end = 90

        overlay = image.copy()
        cv2.rectangle(overlay, (0, 0), (overlay_x_end, overlay_y_end), (0, 0, 0), -1)
        image = cv2.addWeighted(overlay, 0.7, image, 0.3, 0)

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


# ======================== XỬ LÝ HÌNH ẢNH ========================
def process_image(image, confidence_threshold, iou_threshold):
    with st.spinner("🔍 Đang tiến hành nhận diện..."):
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        results = model(image, conf=confidence_threshold, iou=iou_threshold, verbose=False)[0]
        image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        annotated_image, stats = draw_boxes(image_bgr, results)
        return cv2.cvtColor(annotated_image, cv2.COLOR_BGR2RGB), stats


# ======================== XỬ LÝ VIDEO ========================
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

    # Reset violation count khi bắt đầu video mới
    st.session_state.violation_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1

        if frame_count % skip_frames != 0 and frame_count != total_frames:
            progress_percent = min(frame_count / total_frames, 1.0)
            progress_bar.progress(progress_percent)
            status_text.info(f"Đang xử lý... {progress_percent*100:.1f}% hoàn thành")
            continue

        start = time.time()
        resized_frame = cv2.resize(frame, (640, 640))

        results = model(resized_frame, verbose=False, conf=confidence_threshold, iou=iou_threshold)[0]
        actual_fps = 1.0 / (time.time() - start)

        annotated_frame, frame_stats = draw_boxes(resized_frame.copy(), results, actual_fps=actual_fps)

        stats['helmet_counts'].append(frame_stats['with helmet'])
        stats['no_helmet_counts'].append(frame_stats['without helmet'])
        stats['fps_list'].append(actual_fps * 3)
        stats['processed_frames'] += 1

        stframe.image(annotated_frame, channels="BGR", width="stretch")

        progress_percent = min(frame_count / total_frames, 1.0)
        progress_bar.progress(progress_percent)
        status_text.info(f"Đang xử lý... {progress_percent*100:.1f}% hoàn thành")

    cap.release()
    stats['processing_time'] = datetime.now() - stats['start_time']
    status_text.success(f"✅ Xử lý hoàn tất! Thời gian: {stats['processing_time'].seconds} giây")

    total_helmet = sum(stats['helmet_counts'])
    total_no_helmet = sum(stats['no_helmet_counts'])
    total_objects = total_helmet + total_no_helmet
    avg_fps = np.mean(stats['fps_list']) if stats['fps_list'] else 0
    safety_rate = (total_helmet / total_objects * 100) if total_objects > 0 else 0

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
    st.title("Cài đặt")

    st.markdown("---")
    st.markdown("### 🔧 Thông số mô hình")
    confidence_threshold = st.slider("Ngưỡng tin cậy", 0.1, 1.0, 0.5, 0.05)
    iou_threshold = st.slider("Ngưỡng IoU", 0.1, 1.0, 0.4, 0.05)

    st.markdown("---")
    st.markdown("### 🔔 Cảnh báo Telegram")

    current_time = time.time()
    last_alert = st.session_state.alert_history.get("global", 0)
    time_since_last_alert = current_time - last_alert

    if time_since_last_alert < ALERT_COOLDOWN:
        remaining_time = ALERT_COOLDOWN - time_since_last_alert
        st.warning(f"⏳ Cooldown active: {remaining_time:.1f}s remaining")
    else:
        st.success("✅ Alert ready to send")

    st.markdown("---")
    st.markdown("### ℹ️ Thông tin")
    st.markdown("""
    Ứng dụng nhận diện mũ bảo hiểm sử dụng YOLOv11.
    - 🟢: Có đội mũ bảo hiểm
    - 🔴: Không đội mũ bảo hiểm
    """)


# ======================== GIAO DIỆN CHÍNH ========================
st.markdown(
    """
    <h2 style="text-align:center; color: ffffff;">🛡️ Ứng dụng nhận diện không đội mũ bảo hiểm</h2>
    <p style="text-align:center; color:gray;">Hãy chọn nguồn dữ liệu bạn muốn sử dụng để bắt đầu</p>
    """,
    unsafe_allow_html=True
)

source = st.radio("Chọn nguồn dữ liệu:", ["📸 Hình ảnh", "🎥 Video"], horizontal=True, index=0)

if source == "📸 Hình ảnh":
    file = st.file_uploader("Tải ảnh lên", type=["jpg", "jpeg", "png"],
                             help="Chọn ảnh chứa người để phát hiện mũ bảo hiểm")
    if file:
        image = Image.open(file)

        with st.expander("📤 Ảnh đã tải lên", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.image(image, caption="Ảnh gốc", width="stretch")

            with col2:
                result, stats = process_image(np.array(image), confidence_threshold, iou_threshold)
                st.image(result, caption="Kết quả phát hiện", width="stretch")

        st.subheader("📊 Thống kê")
        cols = st.columns(4)
        with cols[0]:
            st.metric("🧍 Tổng đối tượng", stats['total'])
        with cols[1]:
            st.metric("🟢 Có mũ", stats['with helmet'], delta_color="off")
        with cols[2]:
            st.metric("🔴 Không mũ", stats['without helmet'], delta_color="off")
        with cols[3]:
            safety_rate = (stats['with helmet'] / stats['total']) * 100 if stats['total'] > 0 else 0
            st.metric("🔒 Tỷ lệ an toàn", f"{safety_rate:.1f}%")

        st.session_state.report_data.append({
            'Thời gian': datetime.now(),
            'Loại': 'Ảnh',
            'Tổng đối tượng': stats['total'],
            'Có mũ': stats['with helmet'],
            'Không mũ': stats['without helmet'],
            'Tỷ lệ an toàn': f"{safety_rate:.1f}%"
        })

elif source == "🎥 Video":
    file = st.file_uploader("Tải video lên", type=["mp4", "mov", "avi"],
                             help="Chọn video để phân tích theo thời gian thực")
    if file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tfile:
            tfile.write(file.read())
            path = tfile.name

        stats = process_video(path, confidence_threshold, iou_threshold)

        try:
            os.remove(path)
        except:
            pass


# ======================== LỊCH SỬ THỐNG KÊ ========================
if st.session_state.report_data:
    st.markdown("---")
    st.subheader("📊 Lịch sử thống kê")

    df = generate_report()
    st.dataframe(df, width='stretch')

    col1, col2 = st.columns([1, 3])
    with col1:
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "💾 Tải thống kê",
            data=csv,
            file_name=f"helmet_detection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime='text/csv'
        )

    with col2:
        if st.button("🗑️ Xóa toàn bộ lịch sử", type="primary"):
            st.session_state.report_data = []
            st.rerun()