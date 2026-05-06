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


import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
# CSS
def load_css():
    st.markdown("""
    
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

# Tải model
@st.cache_resource
def load_model():
    with st.spinner("🚀 Đang tải mô hình YOLO..."):
        return YOLO("weights/best_helmet3.pt")

model = load_model()


count = 0
from pathlib import Path

VIOLATION_DIR = Path("violations")
VIOLATION_DIR.mkdir(exist_ok=True)

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

    for box in boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = class_names[cls_id]
        print(f'Detected: {label} with confidence {conf:.2f} at [{x1}, {y1}, {x2}, {y2}]')
        if cls_id == 1 and conf > 0.5:
            count += 1
            violation_detected = True
            
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
        send_telegram_alert(str(violation_path), "⚠️ Vi phạm không đội mũ bảo hiểm!")

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

        print("Telegram response:", response.status_code)
        print("Telegram body:", response.text)

        if response.status_code == 200:
            return True
        return False

    except Exception as e:
        print("Telegram send error:", e)
        return False

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
    st.title("Cài đặt")
    
    st.markdown("---")
    st.markdown("### 🔧 Thông số mô hình")
    confidence_threshold = st.slider("Ngưỡng tin cậy", 0.1, 1.0, 0.5, 0.05)
    iou_threshold = st.slider("Ngưỡng IoU", 0.1, 1.0, 0.4, 0.05)
    
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

source = st.radio("Chọn nguồn dữ liệu:", ["📸 Hình ảnh", "🎥 Video"], horizontal=True, index =0)

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
            safety_rate = (stats['helmet'] / stats['total']) * 100 if stats['total'] > 0 else 0
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

# Thống kê tổng quan
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


