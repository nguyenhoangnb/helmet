import time
import os
import cv2
import shutil
import sqlite3
import threading
from queue import Queue
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import uvicorn

from ultralytics import YOLO

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

# ================= CONFIG =================
TARGET_NAME = "Hoàng BK"
PROFILE_PATH = "./zalo_profile"

MODEL_PATH = "../weights/bestyolo.pt"
UPLOAD_DIR = Path("uploads")
VIOLATION_DIR = Path("violations")
DB_PATH = "violations.db"
CONF_THRESH = 0.2

UPLOAD_DIR.mkdir(exist_ok=True)
VIOLATION_DIR.mkdir(exist_ok=True)

# ================= GLOBAL =================
zalo_queue = Queue()
driver = None

# ================= ZALO =================
def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-data-dir={PROFILE_PATH}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # 🔥 chạy nền
    # options.add_argument("--window-size=300,200")
    # options.add_argument("--window-position=-10000,0")

    driver = webdriver.Chrome(options=options)
    driver.get("https://chat.zalo.me/")
    return driver


def find_and_open_chat(driver, name):
    search = driver.find_element(By.XPATH, '//input[@type="text"]')
    search.clear()
    search.send_keys(name)
    time.sleep(2)

    user = driver.find_element(By.XPATH, '(//div[contains(@class,"conv-item")])[1]')
    user.click()
    time.sleep(2)


# ===== CLIPBOARD =====
def copy_image_to_clipboard(image_path):
    # dùng xclip
    os.system(f"xclip -selection clipboard -t image/png -i {image_path}")
    time.sleep(0.5)


def safe_get_msg_box(driver, retries=5):
    for i in range(retries):
        try:
            wait = WebDriverWait(driver, 10)

            msg_box = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@contenteditable="true"]')
                )
            )

            # 🔥 check hiển thị
            if msg_box.is_displayed():
                return msg_box

        except:
            print(f"🔁 Retry msg_box {i+1}")
            time.sleep(1)

    raise Exception("❌ Không tìm thấy msg_box")

import subprocess
import time

def send_image_zalo(image_path):
    global driver
    wait = WebDriverWait(driver, 20)
    image_path = str(Path(image_path).resolve())

    if not os.path.exists(image_path):
        print("❌ Không tìm thấy ảnh:", image_path)
        return

    try:
        # ✅ Copy ảnh vào clipboard bằng xclip
        subprocess.run(
            ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", image_path],
            check=True
        )
        print("✅ Đã copy ảnh vào clipboard")
        time.sleep(0.5)

        # Click vào chat box
        msg_box = wait.until(
            EC.element_to_be_clickable((By.XPATH, '//div[@contenteditable="true"]'))
        )
        msg_box.click()
        time.sleep(0.3)

        # ✅ Paste ảnh từ clipboard bằng Ctrl+V
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
        print("✅ Đã paste ảnh")

        # Đợi preview blob xuất hiện
        wait.until(
            EC.presence_of_element_located((By.XPATH, '//img[contains(@src,"blob:")]'))
        )
        print("✅ Preview xuất hiện")
        time.sleep(0.5)

        # Nhấn Enter để gửi
        msg_box.send_keys(Keys.ENTER)
        print("✅ Gửi ảnh thành công!")

    except Exception as e:
        print("❌ Lỗi:", e)
        driver.save_screenshot("debug_zalo.png")
        import traceback
        traceback.print_exc()
        
# ===== WORKER =====
def zalo_worker():
    global driver

    driver = init_driver()

    print("👉 Login Zalo (20s)...")
    time.sleep(1)

    find_and_open_chat(driver, TARGET_NAME)
    print("✅ Zalo ready")

    while True:
        image_path = zalo_queue.get()

        try:
            send_image_zalo(image_path)
        except Exception as e:
            print("❌ Worker error:", e)

        zalo_queue.task_done()


# ================= YOLO =================
model = YOLO(MODEL_PATH)

# ================= DATABASE =================
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


# ================= FASTAPI =================
app = FastAPI()


@app.post("/upload")
async def upload_image(
    image: UploadFile = File(...),
    camera: str = Form("Camera")
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_path = UPLOAD_DIR / f"{timestamp}.jpg"

    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    results = model(str(upload_path))

    frame = cv2.imread(str(upload_path))
    violation_detected = False
    best_conf = 0

    for box in results[0].boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])

        if cls_id == 1 and conf > CONF_THRESH:
            violation_detected = True
            best_conf = max(best_conf, conf)

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

    if violation_detected:
        violation_path = VIOLATION_DIR / f"violation_{timestamp}.jpg"
        cv2.imwrite(str(violation_path), frame)

        save_violation(camera, "No Helmet", violation_path, best_conf)

        # 🔥 push queue
        zalo_queue.put(str(violation_path))

        return JSONResponse({
            "status": "violation",
            "image": str(violation_path)
        })

    return JSONResponse({"status": "safe"})


# ================= START =================
if __name__ == "__main__":
    threading.Thread(target=zalo_worker, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)