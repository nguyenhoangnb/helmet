from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from ultralytics import YOLO
from datetime import datetime
from pathlib import Path
import sqlite3
import shutil
import cv2
import requests
import uvicorn
import serial

app = FastAPI(title="Helmet Detection Server")
# ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)  # Adjust port and baudrate as needed
violation_frame_count = 0
serial_sent = False

# =========================
# CONFIG
# =========================
MODEL_PATH = "../weights/bestyolo.pt"
UPLOAD_DIR = Path("uploads")
VIOLATION_DIR = Path("violations")
DB_PATH = "violations.db"
CONF_THRESH = 0.6

# Telegram config (optional) via environment variables
import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

UPLOAD_DIR.mkdir(exist_ok=True)
VIOLATION_DIR.mkdir(exist_ok=True)

# Load model
model = YOLO(MODEL_PATH)

# =========================
# DATABASE
# =========================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            camera TEXT,
            violation_type TEXT,
            image_path TEXT,
            confidence REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# =========================
# ALERT
# =========================
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
# =========================
# SAVE DB
# =========================
def save_violation(camera, violation_type, image_path, confidence):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO violations (timestamp, camera, violation_type, image_path, confidence)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        camera,
        violation_type,
        str(image_path),
        confidence
    ))
    conn.commit()
    conn.close()

# =========================
# ROUTES
# =========================
@app.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    camera: str = Form("Unknown Camera")
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_path = UPLOAD_DIR / f"{timestamp}.jpg"
    global violation_frame_count, serial_sent
    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    results = model(str(upload_path))

    violation_detected = False
    best_conf = 0

    frame = cv2.imread(str(upload_path))

    for box in results[0].boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])

        # Assume class 1 = no_helmet
        if cls_id == 1 and conf > CONF_THRESH:
            violation_detected = True
            best_conf = max(best_conf, conf)

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(frame, f"No Helmet {conf:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    if violation_detected:
        violation_path = VIOLATION_DIR / f"violation_{timestamp}.jpg"
        cv2.imwrite(str(violation_path), frame)

        caption = f"[ALERT] No Helmet detected at {camera}\nTime: {datetime.now()}"
        save_violation(camera, "No Helmet", violation_path, best_conf)
        print("Exists:", os.path.exists(str(violation_path)))
        print("Size:", os.path.getsize(str(violation_path)))
        response = send_telegram_alert(str(violation_path), caption)
        # if violation_frame_count >= 5 and not serial_sent:
        #     try:
        #         ser.write(b"1")
        #         print("Sent '1' to serial")
        #         serial_sent = True
        #     except Exception as e:
        #         print("Serial send error:", e)

        return JSONResponse({
            "status": "violation",
            "saved": str(violation_path),
            "confidence": best_conf,
            "response": "Telegram alert sent" if response else "Failed to send Telegram alert"
        })
    else:
        violation_frame_count = 0
        serial_sent = False

    return JSONResponse({"response": "safe"})

@app.get("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM violations ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    return JSONResponse(content={"data": rows})

# =========================
# START
# =========================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
